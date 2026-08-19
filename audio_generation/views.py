import logging
import json
import traceback
from urllib.parse import urljoin
import uuid

import replicate
from django.conf import settings
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from config.celery import app
from audio_generation.models import MinimaxVoiceCloneJob, MinimaxSpeechJob
from audio_generation.serializers import (
    MinimaxVoiceCloneGenerateSerializer, MinimaxVoiceCloneStatusSerializer,
    MinimaxSpeechGenerateSerializer, MinimaxSpeechStatusSerializer
)

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import storage_client
from shared.utils.webhook_utils import (
    generate_webhook_secret,
    generate_webhook_url,
    validate_webhook_secret,
    process_replicate_webhook,
    send_client_webhook
)

# Import Swagger documentation utilities
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

logger = logging.getLogger(__name__)

# Minimax Voice Clone Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate audio using Minimax voice clone model",
    request_body=MinimaxVoiceCloneGenerateSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=MinimaxVoiceCloneStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['POST'])
def generate_minimax_voice_clone(request):
    """
    Generate audio using Minimax voice clone model
    
    POST /api/audio/generate/minimax/voice-clone/
    """
    serializer = MinimaxVoiceCloneGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"MinimaxVoiceCloneGenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        logger.info(f"[VoiceClone] Serializer validated data: {data}")
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the voice clone job record in the database first
        job_id = data.get('id') or uuid.uuid4()
        logger.info(f"[VoiceClone] Attempting to create MinimaxVoiceCloneJob with id: {job_id}")
        voice_clone_job = MinimaxVoiceCloneJob.objects.create(
            id=job_id,
            voice_file=data.get('voice_file'),
            model=data.get('model', 'speech-02-turbo'),
            accuracy=data.get('accuracy', 0.7),
            need_noise_reduction=data.get('need_noise_reduction', False),
            need_volume_normalization=data.get('need_volume_normalization', False),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        logger.info(f"[VoiceClone] Successfully created MinimaxVoiceCloneJob in DB with id: {voice_clone_job.id}")
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'audio_generation:minimax_voice_clone_webhook', 
            voice_clone_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        voice_clone_job.webhook_url = webhook_url
        voice_clone_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing Minimax voice clone task for job {voice_clone_job.id}")
        app.send_task(
            'audio_generation.tasks.generate_minimax_voice_clone',
            args=[str(voice_clone_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': voice_clone_job.id,
            'status': voice_clone_job.status,
            'created_at': voice_clone_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating Minimax voice clone: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Minimax voice clone job",
    responses={
        200: MinimaxVoiceCloneStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['GET'])
def get_minimax_voice_clone_status(request, job_id):
    """
    Get the status of a Minimax voice clone job
    
    GET /api/audio/generate/minimax/voice-clone/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(MinimaxVoiceCloneJob, id=job_id)
        
        # Return the status
        serializer = MinimaxVoiceCloneStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Minimax voice clone status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Minimax voice clone status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['POST'])
def minimax_voice_clone_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Minimax voice clone status updates
    
    POST /api/audio/webhooks/voice-clone/<job_id>/<secret>/
    """
    try:
        logger.info(f"Received webhook for voice clone job {job_id}, method: {request.method}, content_type: {request.content_type}")
        job = get_object_or_404(MinimaxVoiceCloneJob, id=job_id)
        logger.info(f"Found job {job_id} with status: {job.status}")
        
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.error(f"Secret validation failed for job {job_id}. Received: {secret[:4]}..., Expected format: {job.webhook_secret[:4]}...")
            return HttpResponse(status=403)
        
        logger.info(f"Secret validated for job {job_id}")
        payload = json.loads(request.body)
        logger.info(f"Webhook payload for job {job_id}: {json.dumps(payload)}")
        
        success = process_replicate_webhook(payload, job, job.client_webhook_url)
        logger.info(f"Webhook processing result for job {job_id}: {'success' if success else 'failure'}")
        
        if not success:
            logger.error(f"Failed to process webhook for job {job_id}")
            return HttpResponse(status=500)
        
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
            logger.info(f"Updated completed_at timestamp for job {job_id} after success")
        
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Exception in webhook handler for job {job_id}: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Minimax Speech Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate speech using Minimax Speech model",
    request_body=MinimaxSpeechGenerateSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=MinimaxSpeechStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['POST'])
def generate_minimax_speech(request, model_version):
    """
    Generate speech using Minimax Speech model
    
    POST /api/audio/generate/minimax/speech-02-hd/ or /api/audio/generate/minimax/speech-02-turbo/
    """
    serializer = MinimaxSpeechGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"MinimaxSpeechGenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the speech job record in the database first
        speech_job = MinimaxSpeechJob.objects.create(
            text=data.get('text'),
            voice_id=data.get('voice_id', 'Wise_Woman'),
            language=data.get('language', 'en'),
            speed=data.get('speed', 1.0),
            pitch=data.get('pitch', 0),
            volume=data.get('volume', 1.0),
            bitrate=data.get('bitrate', 128000),
            channel=data.get('channel', 'mono'),
            emotion=data.get('emotion', 'auto'),
            sample_rate=data.get('sample_rate', 32000),
            language_boost=data.get('language_boost', 'English'),
            english_normalization=data.get('english_normalization', False),
            model_version=model_version,
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'audio_generation:minimax_speech_webhook', 
            speech_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        speech_job.webhook_url = webhook_url
        speech_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing Minimax speech task for job {speech_job.id}")
        app.send_task(
            'audio_generation.tasks.generate_minimax_speech',
            args=[str(speech_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': speech_job.id,
            'status': speech_job.status,
            'created_at': speech_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating Minimax speech: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Minimax speech job",
    responses={
        200: MinimaxSpeechStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['GET'])
def get_minimax_speech_status(request, model_version, job_id):
    """
    Get the status of a Minimax speech job
    
    GET /api/audio/generate/minimax/speech-02-hd/<job_id>/ or /api/audio/generate/minimax/speech-02-turbo/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(MinimaxSpeechJob, id=job_id)
        
        # Return the status
        serializer = MinimaxSpeechStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Minimax speech status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Minimax speech status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['audio']
)
@api_view(['POST'])
def minimax_speech_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Minimax speech status updates
    
    POST /api/audio/webhooks/speech/<job_id>/<secret>/
    """
    try:
        logger.info(f"Received webhook for speech job {job_id}, method: {request.method}, content_type: {request.content_type}")
        job = get_object_or_404(MinimaxSpeechJob, id=job_id)
        logger.info(f"Found job {job_id} with status: {job.status}")
        
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.error(f"Secret validation failed for job {job_id}. Received: {secret[:4]}..., Expected format: {job.webhook_secret[:4]}...")
            return HttpResponse(status=403)
        
        logger.info(f"Secret validated for job {job_id}")
        payload = json.loads(request.body)
        logger.info(f"Webhook payload for job {job_id}: {json.dumps(payload)}")
        
        # First update model fields from the payload directly in case process_replicate_webhook fails
        try:
            status = payload.get('status')
            if status == 'succeeded' and job.status != 'succeeded':
                job.status = 'succeeded'
                job.completed_at = timezone.now()
                if payload.get('output'):
                    job.output_url = payload.get('output')
                job.save()
                logger.info(f"Direct update of job {job_id} status to succeeded")
        except Exception as direct_update_error:
            logger.error(f"Error in direct status update: {str(direct_update_error)}")
            # Continue to process_replicate_webhook anyway
        
        # Now try the full processing
        success = False
        try:
            success = process_replicate_webhook(payload, job, job.client_webhook_url)
            logger.info(f"Webhook processing result for job {job_id}: {'success' if success else 'failure'}")
        except Exception as process_error:
            logger.error(f"Error in process_replicate_webhook: {str(process_error)}\n{traceback.format_exc()}")
        
        # If job succeeded but processing failed, still mark as success
        if not success and job.status == 'succeeded':
            logger.info(f"Webhook processing failed but job already marked succeeded for {job_id}")
            success = True
        
        if not success:
            logger.error(f"Failed to process webhook for job {job_id}")
            # Return 200 anyway to prevent Replicate from retrying - the job is already marked as succeeded
            return HttpResponse(status=200)
        
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Exception in webhook handler for job {job_id}: {str(e)}\n{traceback.format_exc()}")
        # Return 200 to prevent Replicate from retrying, we've already logged the error
        return HttpResponse(status=200)
