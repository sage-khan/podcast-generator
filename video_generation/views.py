import logging
import json
import traceback
from urllib.parse import urljoin

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

# Import Swagger documentation utilities
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from config.celery import app
from video_generation.models import KlingVideoJob, KlingLipsyncJob, GoogleVeo3VideoJob
from video_generation.serializers import (
    KlingVideoGenerateSerializer, KlingVideoStatusSerializer,
    KlingLipsyncGenerateSerializer, KlingLipsyncStatusSerializer,
    GoogleVeo3GenerateSerializer, GoogleVeo3StatusSerializer
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

logger = logging.getLogger(__name__)

# Kling Video Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate a video using Kling model",
    request_body=KlingVideoGenerateSerializer,
    responses={
        202: openapi.Response(description="Accepted - Job submitted successfully", schema=KlingVideoStatusSerializer),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def generate_kling_video(request):
    """
    Generate a video using Kling model
    
    POST /api/video/generate/kling/1-6/pro/
    """
    serializer = KlingVideoGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"KlingVideoGenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the video job record in the database first
        video_job = KlingVideoJob.objects.create(
            prompt=data.get('prompt'),
            negative_prompt=data.get('negative_prompt', ''),
            aspect_ratio=data.get('aspect_ratio', '16:9'),
            start_image=data.get('start_image'),
            end_image=data.get('end_image'),
            reference_images=data.get('reference_images', []),
            cfg_scale=data.get('cfg_scale', 0.5),
            duration=data.get('duration', 5),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'video_generation:kling_video_webhook', 
            video_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        video_job.webhook_url = webhook_url
        video_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing Kling video generation task for job {video_job.id}")
        app.send_task(
            'video_generation.tasks.generate_kling_video',
            args=[str(video_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': video_job.id,
            'status': video_job.status,
            'created_at': video_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating Kling video: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Kling video generation job",
    responses={
        200: KlingVideoStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['GET'])
def get_kling_video_status(request, job_id):
    """
    Get the status of a Kling video generation job
    
    GET /api/video/generate/kling/1-6/pro/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(KlingVideoJob, id=job_id)
        
        # Return the status
        serializer = KlingVideoStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Kling video status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Kling video generation status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def kling_video_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Kling video generation status updates
    
    POST /api/video/webhooks/kling/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(KlingVideoJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Kling video job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Kling video webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Kling video job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Kling video job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in kling_video_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Kling Lipsync Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate a lip-sync video using Kling model",
    request_body=KlingLipsyncGenerateSerializer,
    responses={
        202: openapi.Response(description="Accepted - Job submitted successfully", schema=KlingLipsyncStatusSerializer),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def generate_kling_lipsync(request):
    """
    Generate a lip-sync video using Kling model
    
    POST /api/video/generate/kling/lipsync/
    """
    serializer = KlingLipsyncGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"KlingLipsyncGenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the lipsync job record in the database
        # Handle both legacy mode and new schema
        job_data = {
            'status': 'starting',
            'webhook_secret': webhook_secret,
            'client_webhook_url': data.get('client_webhook_url'),
            'prompt': data.get('prompt', ''),
            'negative_prompt': data.get('negative_prompt', '')
        }
        
        # Legacy mode (backwards compatibility)
        if data.get('audio_url') and data.get('image_url'):
            job_data.update({
                'audio_url': data.get('audio_url'),
                'image_url': data.get('image_url')
            })
        
        # New schema mode
        else:
            # Text-based input
            job_data.update({
                'text': data.get('text', ''),
                'voice_id': data.get('voice_id', 'en_AOT'),
                'voice_speed': data.get('voice_speed', 1.0)
            })
            
            # Audio input
            if data.get('audio_file'):
                job_data['audio_file'] = data.get('audio_file')
                
            # Video sources
            if data.get('video_id'):
                job_data['video_id'] = data.get('video_id')
            elif data.get('video_url'):
                job_data['video_url'] = data.get('video_url')
        
        # Create the job
        lipsync_job = KlingLipsyncJob.objects.create(**job_data)
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'video_generation:kling_lipsync_webhook', 
            lipsync_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        lipsync_job.webhook_url = webhook_url
        lipsync_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing Kling lipsync task for job {lipsync_job.id}")
        app.send_task(
            'video_generation.tasks.generate_kling_lipsync',
            args=[str(lipsync_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': lipsync_job.id,
            'status': lipsync_job.status,
            'created_at': lipsync_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating Kling lipsync: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Kling lipsync job",
    responses={
        200: KlingLipsyncStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['GET'])
def get_kling_lipsync_status(request, job_id):
    """
    Get the status of a Kling lipsync job
    
    GET /api/video/generate/kling/lipsync/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(KlingLipsyncJob, id=job_id)
        
        # Return the status
        serializer = KlingLipsyncStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Kling lipsync status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Kling lipsync status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def kling_lipsync_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Kling lipsync status updates
    
    POST /api/video/webhooks/lipsync/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(KlingLipsyncJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Kling lipsync job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Kling lipsync webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Kling lipsync job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Kling lipsync job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in kling_lipsync_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Google Veo 3 Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate a video using Google's Veo 3 model",
    request_body=GoogleVeo3GenerateSerializer,
    responses={
        202: openapi.Response(description="Accepted - Job submitted successfully", schema=GoogleVeo3StatusSerializer),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def generate_google_veo3_video(request):
    """
    Generate a video using Google's Veo 3 model
    
    POST /api/videos/generate/google/veo/3
    """
    serializer = GoogleVeo3GenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"GoogleVeo3GenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the video job record in the database first
        video_job = GoogleVeo3VideoJob.objects.create(
            prompt=data.get('prompt'),
            negative_prompt=data.get('negative_prompt', ''),
            enhance_prompt=data.get('enhance_prompt', True),
            seed=data.get('seed'),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'video_generation:google_veo3_webhook', 
            video_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        video_job.webhook_url = webhook_url
        video_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing Google Veo 3 video generation task for job {video_job.id}")
        app.send_task(
            'video_generation.tasks.generate_google_veo3_video',
            args=[str(video_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': video_job.id,
            'status': video_job.status,
            'created_at': video_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating Google Veo 3 video: {str(e)}\n{traceback.format_exc()}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Google Veo 3 video generation job",
    responses={
        200: GoogleVeo3StatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['GET'])
def get_google_veo3_status(request, job_id):
    """
    Get the status of a Google Veo 3 video generation job
    
    GET /api/videos/generate/google/veo/3/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(GoogleVeo3VideoJob, id=job_id)
        
        # Return the status
        serializer = GoogleVeo3StatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Google Veo 3 video status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Google Veo 3 status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['video']
)
@api_view(['POST'])
def google_veo3_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Google Veo 3 status updates
    
    POST /api/videos/webhooks/google/veo/3/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(GoogleVeo3VideoJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Google Veo 3 job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Google Veo 3 webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Google Veo 3 job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Google Veo 3 job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in google_veo3_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)
