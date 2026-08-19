import json
import logging
import traceback
import requests  # Add missing import
import os
import time
import shutil
from uuid import UUID
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import PodcastGenerationJob, PodcastDialogue
from .serializers import (
    PodcastGenerationInputSerializer,
    PodcastGenerationStatusSerializer,
    PodcastGenerationJobListSerializer,
)

# Import Swagger documentation utilities
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

logger = logging.getLogger(__name__)


@swagger_auto_schema(method='post',
    operation_description="Create a new podcast generation job",
    request_body=PodcastGenerationInputSerializer,
    responses={
        201: openapi.Response(description="Created - Job started", schema=PodcastGenerationStatusSerializer),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_podcast_generation_job(request):
    """
    Create a new podcast generation job
    """
    from .tasks import process_podcast_generation
    serializer = PodcastGenerationInputSerializer(data=request.data)
    
    if serializer.is_valid():
        # Create job instance
        job = serializer.save(
            user=request.user,
            status='pending',
            webhook_secret=UUID(int=0).hex,  # Default placeholder that will be updated in the task
            speaker1_webhook_secret=UUID(int=0).hex,
            speaker2_webhook_secret=UUID(int=0).hex if serializer.validated_data.get('speaker_count', 1) == 2 else None
        )
        
        # Assign timestamped media folder and persist
        job.media_folder = f"podcast-gen-{timezone.localtime().strftime('%H-%M-%S-%d-%m-%y')}"
        job.save(update_fields=["media_folder"])
        
        # Start processing
        process_podcast_generation.delay(job.id)
        
        # Return response with job ID
        return Response({
            'id': job.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='get',
    operation_description="Get status of a podcast generation job",
    responses={
        200: PodcastGenerationStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['podcast']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_podcast_generation_status(request, job_id):
    """
    Get status of a podcast generation job
    """
    try:
        job = get_object_or_404(PodcastGenerationJob, id=job_id, user=request.user)
        serializer = PodcastGenerationStatusSerializer(job)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error getting podcast generation status: {str(e)}\n{traceback.format_exc()}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def voice_clone_webhook(request, job_id, speaker_num):
    """
    Webhook handler for voice clone completion
    """
    # Extract secret from query parameters
    secret = request.GET.get('secret')
    
    try:
        # Get job
        job = get_object_or_404(PodcastGenerationJob, id=job_id)
        
        # Verify secret
        if speaker_num == 1:
            expected_secret = job.speaker1_webhook_secret
        else:
            expected_secret = job.speaker2_webhook_secret
            
        if not secret or secret != expected_secret:
            logger.warning(f"Invalid secret for job {job_id} voice clone webhook")
            return HttpResponseBadRequest("Invalid secret")
        
        # Parse webhook data
        try:
            webhook_data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook for job {job_id}")
            return HttpResponseBadRequest("Invalid JSON")
        
        # Extract voice ID from webhook data
        try:
            output = webhook_data.get('output')
            voice_id = None
            if isinstance(output, dict):
                # Replicate returns a dict with a `voice_id` key for Minimax voice clone jobs
                voice_id = output.get('voice_id') or output.get('id')
            else:
                voice_id = output

            if not voice_id:
                logger.error(f"No voice ID in webhook data for job {job_id}")
                return HttpResponseBadRequest("No voice ID in response")

            # Update job with voice ID
            if speaker_num == 1:
                job.speaker1_voice_id = voice_id
                job.save(update_fields=['speaker1_voice_id'])
            else:
                job.speaker2_voice_id = voice_id
                job.save(update_fields=['speaker2_voice_id'])

            logger.info(
                f"Voice clone completed for job {job_id}, speaker {speaker_num}, voice ID: {voice_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing voice clone webhook: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in voice_clone_webhook: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def dialogue_audio_webhook(request, job_id, dialogue_id):
    """
    Webhook handler for dialogue audio generation completion
    """
    from .tasks import try_start_lipsync
    # Extract secret from query parameters
    secret = request.GET.get('secret')
    
    try:
        # Get job and dialogue
        job = get_object_or_404(PodcastGenerationJob, id=job_id)
        dialogue = get_object_or_404(PodcastDialogue, id=dialogue_id, job_id=job_id)
        
        # Determine which speaker's secret to verify
        speaker_name = dialogue.speaker_name
        if speaker_name == job.speaker1_name:
            expected_secret = job.speaker1_webhook_secret
        else:
            expected_secret = job.speaker2_webhook_secret
            
        # Verify secret
        if not secret or secret != expected_secret:
            logger.warning(f"Invalid secret for job {job_id} dialogue {dialogue_id} audio webhook")
            return HttpResponseBadRequest("Invalid secret")
        
        # Parse webhook data
        try:
            webhook_data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook for dialogue {dialogue_id}")
            return HttpResponseBadRequest("Invalid JSON")
        
        # Extract audio URL from webhook data
        try:
            audio_url = webhook_data.get('output')
            if not audio_url:
                logger.error(f"No audio URL in webhook data for dialogue {dialogue_id}")
                return HttpResponseBadRequest("No audio URL in response")
                
            # Update dialogue with audio URL
            dialogue.audio_url = audio_url
            dialogue.status = 'completed'
            dialogue.save(update_fields=['audio_url', 'status'])
                
            logger.info(f"Audio generation completed for dialogue {dialogue_id}, URL: {audio_url}")
            
            # Check if we're ready to start lipsync phase
            try_start_lipsync.delay(job_id)
            
        except Exception as e:
            logger.error(f"Error processing dialogue audio webhook: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in dialogue_audio_webhook: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def speaker_video_webhook(request, job_id, speaker_num):
    """
    Webhook handler for speaker video generation completion
    """
    from .tasks import process_lipsync_for_dialogue
    # Extract secret from query parameters
    secret = request.GET.get('secret')
    
    try:
        # Get job
        job = get_object_or_404(PodcastGenerationJob, id=job_id)
        
        # Verify secret
        if speaker_num == 1:
            expected_secret = job.speaker1_webhook_secret
        else:
            expected_secret = job.speaker2_webhook_secret
            
        if not secret or secret != expected_secret:
            logger.warning(f"Invalid secret for job {job_id} speaker video webhook")
            return HttpResponseBadRequest("Invalid secret")
        
        # Parse webhook data
        try:
            webhook_data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook for job {job_id}")
            return HttpResponseBadRequest("Invalid JSON")
        
        # Extract video URL from webhook data
        try:
            video_url = webhook_data.get('output')
            if not video_url:
                logger.error(f"No video URL in webhook data for job {job_id}")
                return HttpResponseBadRequest("No video URL in response")
                
            # Update job with video URL
            if speaker_num == 1:
                job.speaker1_video_url = video_url
                job.save(update_fields=['speaker1_video_url'])
            else:
                job.speaker2_video_url = video_url
                job.save(update_fields=['speaker2_video_url'])
                
            logger.info(f"Video generation completed for job {job_id}, speaker {speaker_num}, URL: {video_url}")
            
            # Check if both videos are ready for lipsync
            if ((speaker_num == 1 and job.speaker_count == 1) or 
                (job.speaker_count == 2 and job.speaker1_video_url and job.speaker2_video_url)):
                
                # Start lipsync for all dialogues
                dialogues = PodcastDialogue.objects.filter(job_id=job_id, status='completed')
                for dialogue in dialogues:
                    process_lipsync_for_dialogue.delay(dialogue.id)
            
        except Exception as e:
            logger.error(f"Error processing speaker video webhook: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in speaker_video_webhook: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@swagger_auto_schema(method='post',
    operation_description="Webhook handler for lipsync processing callbacks",
    responses={
        200: "OK - Webhook processed successfully",
        400: "Bad Request",
        500: "Internal Server Error"
    },
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([AllowAny])
def lipsync_webhook(request, job_id, dialogue_id):
    """
    Webhook handler for lipsync processing callbacks
    
    Args:
        request: HTTP request
        job_id: ID of the PodcastGenerationJob
        dialogue_id: ID of the PodcastDialogue
    """
    logger.info(f"Received lipsync webhook for job {job_id}, dialogue {dialogue_id}")
    
    # Validate webhook secret
    secret = request.GET.get('secret')
    if not secret:
        logger.warning(f"Missing secret in webhook request for job {job_id}")
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        # Get the job
        job = PodcastGenerationJob.objects.get(id=job_id)
        
        # Compare webhook secret
        if secret != job.webhook_secret:
            logger.warning(f"Invalid secret in webhook request for job {job_id}")
            return Response({"error": "Invalid secret"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get the dialogue
        dialogue = PodcastDialogue.objects.get(id=dialogue_id, job_id=job_id)
        
        # Parse request data
        data = request.data
        
        # Check if lipsync was successful
        if data.get('status') == 'succeeded':
            # Get output URL from the response
            output = data.get('output', {})
            
            # Check if we have a file path in the output
            lipsync_path = None
            
            # Find the output file path
            if isinstance(output, dict) and output.get('output_path'):
                lipsync_path = output['output_path']
            elif isinstance(output, str):
                lipsync_path = output
                
            if not lipsync_path:
                raise ValueError("No lipsync output path in the response")
                
            # Check if the file exists (it should as the model should have saved it)
            if not os.path.exists(lipsync_path):
                raise ValueError(f"Lipsync output file not found at {lipsync_path}")
                
            # Create a public URL for the lipsync video
            # Extract relative path from media root
            media_root = settings.MEDIA_ROOT
            if lipsync_path.startswith(media_root):
                relative_path = lipsync_path[len(media_root):].lstrip('/')
                lipsync_url = f"{settings.MEDIA_URL}{relative_path}"
            else:
                # If not within media root, try to copy to media
                media_base_dir = os.path.join(settings.MEDIA_ROOT, 'podcast-generation', 'tmp')
                os.makedirs(media_base_dir, exist_ok=True)
                
                # Create a filename using our naming convention
                speaker_safe_name = dialogue.speaker_name.replace(" ", "_")
                timestamp = int(time.time())
                lipsync_filename = f"lipsync_{job_id}_{dialogue_id}_{speaker_safe_name}_{timestamp}.mp4"
                
                # New path in our media directory
                new_lipsync_path = os.path.join(media_base_dir, lipsync_filename)
                
                # Copy the file
                shutil.copy2(lipsync_path, new_lipsync_path)
                
                # Create the URL
                relative_path = f"podcast-generation/tmp/{lipsync_filename}"
                lipsync_url = f"{settings.MEDIA_URL}{relative_path}"
            
            # Update dialogue with the lipsync URL
            dialogue.lipsync_url = lipsync_url
            dialogue.status = 'completed'
            dialogue.save(update_fields=['lipsync_url', 'status'])
            
            logger.info(f"Lipsync completed successfully for dialogue {dialogue_id}, URL: {lipsync_url}")
            
            # Check if all lipsync tasks are completed
            from .tasks import check_final_video_readiness
            check_final_video_readiness.delay(job_id)
            
        else:
            # Handle failure
            error_message = data.get('error', 'Unknown error in lipsync processing')
            logger.error(f"Lipsync failed for dialogue {dialogue_id}: {error_message}")
            
            # Update dialogue status
            dialogue.status = 'failed_lipsync'
            dialogue.error_message = error_message
            dialogue.save(update_fields=['status', 'error_message'])
            
            # Check if this failure should affect the entire job
            check_final_video_readiness.delay(job_id)
        
        return Response({"status": "received"}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing lipsync webhook for job {job_id}, dialogue {dialogue_id}: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def final_video_webhook(request, job_id):
    """
    Webhook handler for final video combination completion
    """
    # Extract secret from query parameters
    secret = request.GET.get('secret')
    
    try:
        # Get job
        job = get_object_or_404(PodcastGenerationJob, id=job_id)
        
        # Verify secret
        if not secret or secret != job.webhook_secret:
            logger.warning(f"Invalid secret for job {job_id} final video webhook")
            return HttpResponseBadRequest("Invalid secret")
        
        # Parse webhook data
        try:
            webhook_data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook for job {job_id}")
            return HttpResponseBadRequest("Invalid JSON")
        
        # Extract final video URL from webhook data
        try:
            final_video_url = webhook_data.get('output')
            if not final_video_url:
                logger.error(f"No final video URL in webhook data for job {job_id}")
                return HttpResponseBadRequest("No final video URL in response")
                
            # Update job with final video URL and mark as completed
            job.final_video_url = final_video_url
            job.final_video_status = 'completed'
            job.status = 'completed'
            job.save(update_fields=['final_video_url', 'final_video_status', 'status'])
                
            logger.info(f"Final video generation completed for job {job_id}, URL: {final_video_url}")
            
            # Notify the client if webhook URL is provided
            if job.client_webhook_url:
                data = {
                    'job_id': str(job.id),
                    'status': 'completed',
                    'output': final_video_url
                }
                try:
                    requests.post(job.client_webhook_url, json=data, timeout=10)
                except Exception as webhook_error:
                    logger.error(f"Error sending webhook to client: {str(webhook_error)}")
            
        except Exception as e:
            logger.error(f"Error processing final video webhook: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in final_video_webhook: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@swagger_auto_schema(method='post',
    operation_description="Generate a podcast script based on topic and speaker information",
    responses={
        200: "OK - Script generated successfully",
        400: "Bad Request",
        500: "Internal Server Error"
    },
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_script(request):
    """
    Generate a podcast script based on topic and speaker information
    """
    from .tasks import generate_podcast_script
    try:
        # Get the data from the request
        topic = request.data.get('topic')
        speaker_count = request.data.get('speaker_count')
        speaker1_name = request.data.get('speaker1_name')
        speaker2_name = request.data.get('speaker2_name', None)
        speaker1_audio = request.data.get('speaker1_audio', None)
        speaker2_audio = request.data.get('speaker2_audio', None)
        
        # Validate input
        if not topic:
            return Response(
                {"error": "Topic is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not speaker_count or speaker_count not in [1, 2]:
            return Response(
                {"error": "Speaker count must be 1 or 2"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not speaker1_name:
            return Response(
                {"error": "Speaker 1 name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if speaker_count == 2 and not speaker2_name:
            return Response(
                {"error": "Speaker 2 name is required when speaker_count is 2"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare speaker names list
        speaker_names = [speaker1_name]
        if speaker_count == 2:
            speaker_names.append(speaker2_name)
        
        # Prepare speaker audios list if provided
        speaker_audios = []
        if speaker1_audio:
            speaker_audios.append(speaker1_audio)
            
        if speaker_count == 2 and speaker2_audio:
            if not speaker1_audio:
                # Need to add None for speaker1_audio if it's not provided but speaker2_audio is
                speaker_audios.append(None)
            speaker_audios.append(speaker2_audio)
        
        # Generate the script
        result = generate_podcast_script(topic, speaker_count, speaker_names,
                                        speaker_audios if speaker_audios else None)
        
        # Return the result
        response_data = {
            "status": "success",
            "topic": topic,
            "speaker_count": speaker_count,
            "speaker_names": speaker_names,
            "dialogue_segments": result["dialogue_segments"],
            "output_file": result["output_file"]
        }
        
        # Add voice cloning job information if available
        if 'voice_clone_jobs' in result:
            response_data['voice_clone_jobs'] = result['voice_clone_jobs']
            
        return Response(response_data, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in generate_script view: {str(e)}")
        logger.error(traceback.format_exc())
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# -----------------------------------------------------------------------------
# Wrapper endpoints per 2025 README
# -----------------------------------------------------------------------------

@swagger_auto_schema(method='post',
    operation_description="Generate a monologue podcast script (wrapper)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'prompt': openapi.Schema(type=openapi.TYPE_STRING),
            'pdf_content': openapi.Schema(type=openapi.TYPE_STRING, description='Base64-encoded PDF'),
            'speaker_name': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['prompt'],
    ),
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_script_monologue(request):
    """Wrapper around generate_script setting speaker_count=1."""
    mutable_data = request.data.copy()
    mutable_data['speaker_count'] = 1
    # Rename prompt->topic for internal function
    if 'prompt' in mutable_data and 'topic' not in mutable_data:
        mutable_data['topic'] = mutable_data.pop('prompt')
    request._full_data = mutable_data  # hacky but works for wrapper
    return generate_script(request)


@swagger_auto_schema(method='post',
    operation_description="Generate a dialogue podcast script (wrapper)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'prompt': openapi.Schema(type=openapi.TYPE_STRING),
            'pdf_content': openapi.Schema(type=openapi.TYPE_STRING),
            'speaker1_name': openapi.Schema(type=openapi.TYPE_STRING),
            'speaker2_name': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['prompt', 'speaker1_name', 'speaker2_name'],
    ),
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_script_dialogue(request):
    """Wrapper around generate_script setting speaker_count=2."""
    mutable_data = request.data.copy()
    mutable_data['speaker_count'] = 2
    if 'prompt' in mutable_data and 'topic' not in mutable_data:
        mutable_data['topic'] = mutable_data.pop('prompt')
    request._full_data = mutable_data
    return generate_script(request)


# ---------------- Full podcast creation wrappers ----------------------------

@swagger_auto_schema(method='post',
    operation_description="Create a monologue podcast (full pipeline)",
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_podcast_monologue(request):
    """Wrapper setting speaker_count=1 for full podcast creation."""
    # Extract data from request and translate common client aliases
    data = request.data.copy()

    # 1 speaker for monologue
    data['speaker_count'] = 1

    # Allow "prompt" instead of "podcast_topic"
    if 'prompt' in data and 'podcast_topic' not in data:
        data['podcast_topic'] = data.pop('prompt')

    # Single-speaker convenience aliases
    alias_map = {
        'speaker_name': 'speaker1_name',
        'speaker_image': 'speaker1_image',
        'speaker_audio': 'speaker1_audio',          # Some clients still send this
        'speaker_audio_sample': 'speaker1_audio',   # Older scripts send this key
        'speaker_video': 'speaker1_video',
        'speaker_voice_clone_ID': 'speaker1_voice_clone_ID',
        'webhook_url': 'client_webhook_url',
        'background_image': 'background_image_reference',
    }

    for old, new in alias_map.items():
        if old in data and new not in data:
            data[new] = data.pop(old)

    # Use the same serializer and logic as the main endpoint
    serializer = PodcastGenerationInputSerializer(data=data)

    if serializer.is_valid():
        # Create job instance
        job = serializer.save(
            user=request.user,
            status='pending',
            webhook_secret=UUID(int=0).hex,
            speaker1_webhook_secret=UUID(int=0).hex,
            speaker2_webhook_secret=None  # Only 1 speaker for monologue
        )
        
        # Assign timestamped media folder and persist
        job.media_folder = f"podcast-gen-{timezone.localtime().strftime('%H-%M-%S-%d-%m-%y')}"
        job.save(update_fields=["media_folder"])
        
        # Start processing
        from .tasks import process_podcast_generation
        process_podcast_generation.delay(job.id)

        # Return response with job ID
        return Response({
            'id': job.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
    operation_description="Create a dialogue podcast (full pipeline)",
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_podcast_dialogue(request):
    """Wrapper setting speaker_count=2 for full podcast creation."""
    data = request.data.copy()
    data['speaker_count'] = 2

    # Allow "prompt" instead of "podcast_topic"
    if 'prompt' in data and 'podcast_topic' not in data:
        data['podcast_topic'] = data.pop('prompt')

    # Translate convenience aliases for dialogue
    alias_map = {
        'speaker1_audio_sample': 'speaker1_audio',
        'speaker2_audio_sample': 'speaker2_audio',
        'speaker1_audio': 'speaker1_audio',  # Accept both variants
        'speaker2_audio': 'speaker2_audio',
        'speaker1_image': 'speaker1_image',
        'speaker2_image': 'speaker2_image',
        'speaker1_video': 'speaker1_video',
        'speaker2_video': 'speaker2_video',
        'background_image': 'background_image_reference',
        'webhook_url': 'client_webhook_url',
    }

    for old, new in alias_map.items():
        if old in data and new not in data:
            data[new] = data.pop(old)

    serializer = PodcastGenerationInputSerializer(data=data)

    if serializer.is_valid():
        # Create job instance
        job = serializer.save(
            user=request.user,
            status='pending',
            webhook_secret=UUID(int=0).hex,
            speaker1_webhook_secret=UUID(int=0).hex,
            speaker2_webhook_secret=UUID(int=0).hex  # Two speakers for dialogue
        )
        
        # Assign timestamped media folder and persist
        job.media_folder = f"podcast-gen-{timezone.localtime().strftime('%H-%M-%S-%d-%m-%y')}"
        job.save(update_fields=["media_folder"])
        
        # Start processing
        from .tasks import process_podcast_generation
        process_podcast_generation.delay(job.id)

        # Return response with job ID
        return Response({
            'id': job.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------
# New job management endpoints (list + cancel)
# -----------------------------------------------------------------------------

@swagger_auto_schema(method='get',
    operation_description="List podcast generation jobs for the authenticated user (most recent first).",
    responses={200: PodcastGenerationJobListSerializer(many=True)},
    tags=['podcast']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_podcast_jobs(request):
    """Return a paginated list of the caller's PodcastGenerationJob objects."""
    qs = PodcastGenerationJob.objects.filter(user=request.user).order_by('-created_at')

    # Basic page-number pagination (page & page_size query params)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    serializer = PodcastGenerationJobListSerializer(qs[start:end], many=True)

    return Response({
        'count': qs.count(),
        'page': page,
        'page_size': page_size,
        'results': serializer.data,
    })


@swagger_auto_schema(method='post',
    operation_description="Cancel a pending/processing podcast generation job.",
    responses={200: "Cancellation requested", 400: "Bad Request", 404: "Not Found"},
    tags=['podcast']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_podcast_job(request, job_id):
    """Mark a job as cancelled if it is still in progress."""
    job = get_object_or_404(PodcastGenerationJob, id=job_id, user=request.user)

    if job.status in {'completed', 'failed', 'cancelled'}:
        return Response({'detail': f'Job already {job.status}.'}, status=status.HTTP_400_BAD_REQUEST)

    job.status = 'cancelled'
    job.save(update_fields=['status'])

    # Note: For simplicity we do not revoke individual Celery tasks here; workers
    # should periodically check job.status and abort early where feasible.

    return Response({'detail': 'Cancellation requested', 'status': 'cancelled'})