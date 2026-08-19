import logging
import json
import re
import uuid
import secrets
import traceback
import urllib.parse
from urllib.parse import urljoin

import replicate
from django.conf import settings
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, parser_classes, action
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from django.conf import settings
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render

from config.celery import app
from image_generation.models import (
    Character, Pose, LoraGenerationJob, FluxUltraProJob, 
    FluxKontextProJob, FluxKontextMultiJob, FluxKontextMultiListJob,
    FluxKontextPortraitSeriesJob
)
from image_generation.serializers import (
    CharacterSerializer, PoseSerializer, 
    CharacterGenerateSerializer, PoseGenerateSerializer,
    CharacterStatusSerializer, PoseStatusSerializer,
    LoraGenerationInputSerializer, LoraGenerationStatusSerializer,
    FluxUltraProInputSerializer, FluxUltraProStatusSerializer,
    FluxKontextProInputSerializer, FluxKontextProStatusSerializer,
    FluxKontextMultiInputSerializer, FluxKontextMultiStatusSerializer,
    FluxKontextMultiListInputSerializer, FluxKontextMultiListStatusSerializer,
    FluxKontextPortraitSeriesInputSerializer, FluxKontextPortraitSeriesStatusSerializer
)
from django.views.decorators.csrf import csrf_exempt

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import storage_client
from shared.utils.webhook_utils import (
    generate_webhook_secret, 
    generate_webhook_url, 
    validate_webhook_secret,
    process_replicate_webhook,
    send_client_webhook
)

from image_generation.tasks import generate_flux_kontext_portrait_series as portrait_series_task

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

logger = logging.getLogger(__name__)

# Character generation views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate a character using Flux model",
    request_body=CharacterGenerateSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=CharacterStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_character(request):
    """
    Generate a character using Flux model
    
    POST /api/images/generate/
    """
    serializer = CharacterGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"CharacterGenerateSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the character record in the database first
        character = Character.objects.create(
            prompt=data.get('prompt'),
            negative_prompt=data.get('negative_prompt'),
            image_url="",  # Will be populated later
            replicate_url="",  # Will be populated later
            seed=data.get('seed'),
            aspect_ratio=data.get('aspect_ratio', "1:1"),
            image_prompt=data.get('image_prompt'),
            output_format=data.get('output_format', "jpg"),
            output_quality=data.get('output_quality', 80),
            safety_tolerance=data.get('safety_tolerance', 2),
            image_prompt_strength=data.get('image_prompt_strength', 0.1),
            raw=data.get('raw', False),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'image_generation:character_webhook', 
            character.id, 
            webhook_secret, 
            request
        )
        
        # Initialize the Replicate client
        client = ReplicateClient()
        
        # Prepare the generation parameters
        gen_params = {
            "prompt": data.get('prompt'),
        }
        
        # Add optional parameters if provided
        if data.get('negative_prompt'):
            gen_params['negative_prompt'] = data.get('negative_prompt')
        
        if data.get('seed') is not None:
            gen_params['seed'] = data.get('seed')
            
        if data.get('aspect_ratio'):
            gen_params['aspect_ratio'] = data.get('aspect_ratio')
            
        if data.get('image_prompt'):
            gen_params['image_prompt'] = data.get('image_prompt')
            gen_params['image_prompt_strength'] = data.get('image_prompt_strength', 0.1)
            
        if data.get('output_format'):
            gen_params['output_format'] = data.get('output_format')
            
        if data.get('output_quality'):
            gen_params['output_quality'] = data.get('output_quality')
            
        if data.get('safety_tolerance'):
            gen_params['safety_tolerance'] = data.get('safety_tolerance')
            
        if data.get('raw') is not None:
            gen_params['raw'] = data.get('raw')
        
        # Start the generation job
        logger.info(f"Starting character generation for prompt: {data.get('prompt')[:50]}...")
        prediction = client.generate_character(
            **gen_params,
            webhook=webhook_url,
            webhook_events_filter=["start", "output", "logs", "completed"]
        )
        
        # Update the character with the prediction ID
        if prediction and hasattr(prediction, 'id'):
            character.replicate_prediction_id = prediction.id
            character.status = 'processing'
            character.save()
            
            logger.info(f"Character generation job started with prediction ID: {prediction.id}")
            
            # Return the character data
            response_data = {
                'id': character.id,
                'status': character.status,
                'message': 'Character generation job started successfully',
                'replicate_prediction_id': character.replicate_prediction_id
            }
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
        else:
            # Handle the error case
            character.status = 'failed'
            character.error_message = "Failed to start generation job"
            character.save()
            
            logger.error(f"Failed to start character generation job: {prediction}")
            return Response(
                {"error": "Failed to start generation job", "details": str(prediction)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in generate_character: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate poses for a character or based on an image URL",
    request_body=PoseGenerateSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=PoseStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_poses(request):
    """
    Generate poses for a character or based on an image URL
    
    POST /api/images/generate/poses/
    """
    try:
        # Parse and validate input data
        serializer = PoseGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create pose instance
        pose_id = uuid.uuid4()
        pose = Pose(
            id=pose_id,
            status='pending',
            pose_prompt=data.get('pose_prompt', ''),
            pose_type=data.get('pose_type', '')
        )
        
        # Set up client webhook URL if provided
        client_webhook_url = data.get('client_webhook_url')
        pose.client_webhook_url = client_webhook_url
        
        # Generate a webhook URL for Replicate
        webhook_secret = generate_webhook_secret()
        webhook_url = generate_webhook_url(request, 'pose_webhook', args=[str(pose_id), webhook_secret])
        
        # Handle either character-based or direct image URL-based generation
        if 'character_id' in data and data['character_id']:
            # Get the character from the database
            try:
                character = Character.objects.get(pk=data['character_id'])
            except Character.DoesNotExist:
                return Response(
                    {"error": f"Character with ID {data['character_id']} not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            pose.character = character
            pose.save()
            
            # Initialize the Replicate client
            client = ReplicateClient()
            
            # Set up generation parameters
            gen_params = {
                'character_image': character.image_url,
            }
            logger.info(f"Using character image: {character.image_url}")
        else:
            # Direct image URL input path
            if not data.get('subject'):
                return Response(
                    {"error": "When character_id is not provided, subject (image URL) is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create a temporary character to associate with this pose
            temp_character = Character(
                id=uuid.uuid4(),
                status='succeeded',
                prompt=data.get('prompt', 'A headshot photo'),
                negative_prompt=data.get('negative_prompt', ''),
                image_url=data.get('subject'),
                aspect_ratio=data.get('aspect_ratio', '1:1'),
                output_format=data.get('output_format', 'webp'),
                output_quality=data.get('output_quality', 80),
                safety_tolerance=data.get('safety_tolerance', 2)
            )
            temp_character.save()
            
            pose.character = temp_character
            pose.save()
            
            # Initialize the Replicate client
            client = ReplicateClient()
            
            # Set up generation parameters
            gen_params = {
                'character_image': data.get('subject'),
            }
            logger.info(f"Using direct image URL: {data.get('subject')}")
        
        # Common parameters for both paths
        if data.get('pose_prompt'):
            gen_params['pose_prompt'] = data.get('pose_prompt')
        if data.get('pose_type'):
            gen_params['pose_type'] = data.get('pose_type')
        if data.get('seed') is not None:
            gen_params['seed'] = data.get('seed')
        if data.get('aspect_ratio'):
            gen_params['aspect_ratio'] = data.get('aspect_ratio')
        if data.get('output_format'):
            gen_params['output_format'] = data.get('output_format')
        if data.get('output_quality') is not None:
            gen_params['output_quality'] = data.get('output_quality')
        if data.get('negative_prompt'):
            gen_params['negative_prompt'] = data.get('negative_prompt')
        if data.get('randomise_poses') is not None:
            gen_params['randomise_poses'] = data.get('randomise_poses')
        if data.get('number_of_outputs') is not None:
            gen_params['number_of_outputs'] = data.get('number_of_outputs')
        if data.get('disable_safety_checker') is not None:
            gen_params['disable_safety_checker'] = data.get('disable_safety_checker')
        if data.get('number_of_images_per_pose') is not None:
            gen_params['number_of_images_per_pose'] = data.get('number_of_images_per_pose')
        
        # Start the pose generation job
        logger.info(f"Starting pose generation for {'character' if 'character_id' in data else 'direct image URL'}")
        prediction = client.generate_poses(
            **gen_params,
            webhook=webhook_url,
            webhook_events_filter=["start", "output", "logs", "completed"]
        )
        
        # Update the pose with the prediction ID
        if prediction and hasattr(prediction, 'id'):
            pose.replicate_prediction_id = prediction.id
            pose.status = 'processing'
            pose.save()
            
            # Return a success response
            serializer = PoseStatusSerializer(data={
                'id': pose.id,
                'character_id': pose.character.id,
                'status': pose.status,
                'created_at': pose.created_at
            })
            serializer.is_valid()
            
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            # Handle the error case
            pose.status = 'failed'
            pose.error_message = "Failed to start generation job"
            pose.save()
            
            logger.error(f"Failed to start pose generation job: {prediction}")
            return Response(
                {"error": "Failed to start generation job", "details": str(prediction)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in pose generation: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a character generation job",
    responses={
        200: CharacterStatusSerializer,
        404: "Not Found - Character does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_character_status(request, character_id):
    """
    Get the status of a character generation job
    
    GET /api/images/generate/status/<character_id>/
    """
    try:
        logger.info(f"Received GET request for character status: {character_id}")
        character = get_object_or_404(Character, pk=character_id)
        
        serializer = CharacterStatusSerializer({
            'id': character.id,
            'prompt': character.prompt,
            'status': character.status,
            'created_at': character.created_at,
            'image_url': character.image_url if character.status == 'succeeded' else None,
            'replicate_url': character.replicate_url if character.status == 'succeeded' else None,
            'output_urls': character.output_urls if character.status == 'succeeded' else None,
            'error_message': character.error_message if character.status == 'failed' else None
        })
        
        logger.info(f"Returning status for character {character_id}: {character.status}")
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error retrieving status for character {character_id}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a pose generation job",
    responses={
        200: PoseStatusSerializer,
        404: "Not Found - Pose does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_pose_status(request, pose_id):
    """
    Get the status of a pose generation job
    
    GET /api/images/generate/poses/status/<pose_id>/
    """
    try:
        logger.info(f"Received GET request for pose status: {pose_id}")
        pose = get_object_or_404(Pose, pk=pose_id)
        
        serializer = PoseStatusSerializer({
            'id': pose.id,
            'character_id': pose.character.id,
            'status': pose.status,
            'created_at': pose.created_at,
            'image_url': pose.image_url if pose.status == 'succeeded' else None,
            'replicate_url': pose.replicate_url if pose.status == 'succeeded' else None,
            'output_urls': pose.output_urls if pose.status == 'succeeded' else None,
            'error_message': pose.error_message if pose.status == 'failed' else None
        })
        
        logger.info(f"Returning status for pose {pose_id}: {pose.status}")
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error retrieving status for pose {pose_id}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send character generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def character_webhook(request, character_id, secret):
    """
    Webhook endpoint for Replicate to send character generation status updates
    
    POST /api/webhooks/character/<character_id>/<secret>/
    """
    try:
        # Get the Character instance
        character = get_object_or_404(Character, pk=character_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, character.webhook_secret):
            logger.warning(f"Invalid webhook secret for character {character_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Character webhook received: {payload.get('status')} for {character_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for character {character_id}")
            return HttpResponse(status=400)
        
        # Process the webhook using the shared utility
        success = process_replicate_webhook(
            payload, 
            character, 
            character.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for character {character_id}")
            return HttpResponse(status=500)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in character_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send pose generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def pose_webhook(request, pose_id, secret):
    """
    Webhook endpoint for Replicate to send pose generation status updates
    
    POST /api/webhooks/pose/<pose_id>/<secret>/
    """
    try:
        # Get the Pose instance
        pose = get_object_or_404(Pose, pk=pose_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, pose.webhook_secret):
            logger.warning(f"Invalid webhook secret for pose {pose_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Pose webhook received: {payload.get('status')} for {pose_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for pose {pose_id}")
            return HttpResponse(status=400)
        
        # Process the webhook using the shared utility
        success = process_replicate_webhook(
            payload, 
            pose, 
            pose.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for pose {pose_id}")
            return HttpResponse(status=500)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in pose_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


class CharacterViewSet(viewsets.ModelViewSet):
    """API endpoint for character management"""
    queryset = Character.objects.all().order_by('-created_at')
    serializer_class = CharacterSerializer
    
    @swagger_auto_schema(
        operation_description="Get characters filtered by user",
        responses={
            200: CharacterSerializer(many=True),
            400: "Bad Request",
        },
        tags=['images']
    )
    def get_queryset(self):
        queryset = Character.objects.all().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset
    
    @swagger_auto_schema(method='get',
        operation_description="Get poses for a specific character",
        responses={
            200: PoseSerializer(many=True),
            404: "Not Found - Character does not exist"
        },
        tags=['images']
    )
    @action(detail=True, methods=['get'])
    def poses(self, request, pk=None):
        """Get poses for a specific character"""
        character = self.get_object()
        poses = character.poses.all()
        serializer = PoseSerializer(poses, many=True)
        return Response(serializer.data)


class PoseViewSet(viewsets.ModelViewSet):
    """API endpoint for pose management"""
    queryset = Pose.objects.all().order_by('-created_at')
    serializer_class = PoseSerializer
    
    @swagger_auto_schema(method='get',
        operation_description="Get poses by character ID",
        manual_parameters=[
            openapi.Parameter(
                'character_id',
                openapi.IN_QUERY,
                description="Filter by character ID",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: PoseSerializer(many=True),
            400: "Bad Request - Missing character ID"
        },
        tags=['images']
    )
    @action(detail=False, methods=['get'])
    def by_character(self, request):
        """Get poses by character ID"""
        character_id = request.query_params.get('character_id')
        if not character_id:
            return Response(
                {"error": "character_id query parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        poses = Pose.objects.filter(character_id=character_id).order_by('-created_at')
        serializer = self.get_serializer(poses, many=True)
        return Response(serializer.data)


# LoRA Image Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate images using a fine-tuned LoRA model",
    request_body=LoraGenerationInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=LoraGenerationStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_with_lora(request):
    """
    Generate images using a fine-tuned LoRA model
    
    POST /api/image-generation/finetuned/lora/flux-1/
    """
    serializer = LoraGenerationInputSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"LoraGenerationInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the LoRA generation job record in the database
        generation_job = LoraGenerationJob.objects.create(
            model_id=data['model_id'],
            prompt=data['prompt'],
            negative_prompt=data.get('negative_prompt', ''),
            status='queued',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url'),
            webhook_events_filter=data.get('webhook_events_filter', ["completed", "output"]),
            
            # Store all the parameters for the generation
            num_outputs=data.get('num_outputs', 4),
            seed=data.get('seed'),
            go_fast=data.get('go_fast', False),
            lora_scale=data.get('lora_scale', 1.0),
            megapixels=data.get('megapixels', '1'),
            aspect_ratio=data.get('aspect_ratio', '1:1'),
            output_format=data.get('output_format', 'webp'),
            guidance_scale=data.get('guidance_scale', 3.0),
            output_quality=data.get('output_quality', 80),
            prompt_strength=data.get('prompt_strength', 0.8),
            extra_lora_scale=data.get('extra_lora_scale', 1.0),
            num_inference_steps=data.get('num_inference_steps', 28)
        )
        
        # Add width and height for custom aspect ratio
        if data.get('aspect_ratio') == 'custom':
            generation_job.width = data.get('width', 512)
            generation_job.height = data.get('height', 512) 
            generation_job.save(update_fields=['width', 'height'])
        
        # Generate webhook URL for Replicate
        webhook_url = generate_webhook_url(
            'image_generation:lora_generation_webhook', 
            generation_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL
        generation_job.webhook_url = webhook_url
        generation_job.save(update_fields=['webhook_url'])
        
        # Queue the background task
        logger.info(f"Queueing LoRA generation task for job {generation_job.id}")
        app.send_task(
            'image_generation.tasks.generate_with_lora',
            args=[str(generation_job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': generation_job.id,
            'model_id': generation_job.model_id,
            'status': generation_job.status,
            'created_at': generation_job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating with LoRA model: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a LoRA generation job",
    responses={
        200: LoraGenerationStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_lora_generation_status(request, job_id):
    """
    Get the status of a LoRA generation job
    
    GET /api/image-generation/finetuned/lora/flux-1/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(LoraGenerationJob, id=job_id)
        
        # Return the status
        serializer = LoraGenerationStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting LoRA generation status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send LoRA generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def lora_generation_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send LoRA generation status updates
    
    POST /api/image-generation/webhooks/lora/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(LoraGenerationJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for LoRA generation job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"LoRA generation webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for LoRA generation job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for LoRA generation job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in lora_generation_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Flux UltraPro Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate an image using Flux-1.1-UltraPro model",
    request_body=FluxUltraProInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=FluxUltraProStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_flux_ultrapro(request):
    """
    Generate an image using Flux-1.1-UltraPro model
    
    POST /api/images/generate/flux/1-1/pro/
    """
    serializer = FluxUltraProInputSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"FluxUltraProInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the job record in the database
        job = FluxUltraProJob.objects.create(
            prompt=data.get('prompt'),
            negative_prompt=data.get('negative_prompt'),
            seed=data.get('seed'),
            aspect_ratio=data.get('aspect_ratio', "1:1"),
            image_prompt=data.get('image_prompt'),
            output_format=data.get('output_format', "png"),
            safety_tolerance=data.get('safety_tolerance', 2),
            image_prompt_strength=data.get('image_prompt_strength', 0.1),
            raw=data.get('raw', False),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url'),
            webhook_events_filter=data.get('webhook_events_filter', ["start", "output", "completed"])
        )
        
        # Generate webhook URL for Replicate
        webhook_url = generate_webhook_url(
            'image_generation:flux_ultrapro_webhook', 
            job.id, 
            webhook_secret, 
            request
        )
        
        # Queue the background task
        logger.info(f"Queueing Flux UltraPro generation task for job {job.id}")
        app.send_task(
            'image_generation.tasks.generate_flux_ultrapro',
            args=[str(job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating with Flux UltraPro: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Flux UltraPro generation job",
    responses={
        200: FluxUltraProStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_flux_ultrapro_status(request, job_id):
    """
    Get the status of a Flux UltraPro generation job
    
    GET /api/images/generate/flux/1-1/pro/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(FluxUltraProJob, id=job_id)
        
        # Return the status
        serializer = FluxUltraProStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Flux UltraPro generation status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Flux UltraPro generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def flux_ultrapro_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Flux UltraPro generation status updates
    
    POST /api/webhooks/flux/ultrapro/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(FluxUltraProJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Flux UltraPro job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Flux UltraPro webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Flux UltraPro job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Flux UltraPro job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in flux_ultrapro_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Flux Kontext Pro Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate images using Flux Kontext Pro model",
    request_body=FluxKontextProInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=FluxKontextProStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_flux_kontextpro(request):
    """
    Generate an image using Flux Kontext Pro model
    
    POST /api/images/generate/flux/kontext/pro/
    """
    serializer = FluxKontextProInputSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"FluxKontextProInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the job record in the database
        job = FluxKontextProJob.objects.create(
            prompt=data.get('prompt'),
            input_image=data.get('input_image'),
            seed=data.get('seed'),
            aspect_ratio=data.get('aspect_ratio', "match_input_image"),
            output_format=data.get('output_format', "png"),
            safety_tolerance=data.get('safety_tolerance', 2),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url'),
            webhook_events_filter=data.get('webhook_events_filter', ["start", "output", "completed"])
        )
        
        # Generate webhook URL for Replicate
        webhook_url = generate_webhook_url(
            'image_generation:flux_kontextpro_webhook', 
            job.id, 
            webhook_secret, 
            request
        )
        
        # Queue the background task
        logger.info(f"Queueing Flux Kontext Pro generation task for job {job.id}")
        app.send_task(
            'image_generation.tasks.generate_flux_kontextpro',
            args=[str(job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating with Flux Kontext Pro: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Flux Kontext Pro generation job",
    responses={
        200: FluxKontextProStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_flux_kontextpro_status(request, job_id):
    """
    Get the status of a Flux Kontext Pro generation job
    
    GET /api/images/generate/flux/kontext/pro/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(FluxKontextProJob, id=job_id)
        
        # Return the status
        serializer = FluxKontextProStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Flux Kontext Pro generation status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Flux Kontext Pro generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def flux_kontextpro_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Flux Kontext Pro generation status updates
    
    POST /api/webhooks/flux/kontextpro/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(FluxKontextProJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Flux Kontext Pro job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Flux Kontext Pro webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Flux Kontext Pro job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Flux Kontext Pro job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in flux_kontextpro_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Flux Kontext Multi-image Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate images using Flux Kontext Multi-image model",
    request_body=FluxKontextMultiInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=FluxKontextMultiStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_flux_kontext_multi(request):
    """
    Generate an image using Flux Kontext Multi-image model
    
    POST /api/images/generate/flux/kontext/multi-image/
    """
    serializer = FluxKontextMultiInputSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"FluxKontextMultiInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a secret for the webhook
        webhook_secret = generate_webhook_secret()
        
        # Create the job record in the database
        job = FluxKontextMultiJob.objects.create(
            prompt=data.get('prompt'),
            input_image_1=data.get('input_image_1'),
            input_image_2=data.get('input_image_2'),
            seed=data.get('seed'),
            aspect_ratio=data.get('aspect_ratio', "match_input_image"),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url'),
            webhook_events_filter=data.get('webhook_events_filter', ["start", "output", "completed"])
        )
        
        # Generate webhook URL for Replicate
        webhook_url = generate_webhook_url(
            'image_generation:flux_kontext_multi_webhook', 
            job.id, 
            webhook_secret, 
            request
        )
        
        # Queue the background task
        logger.info(f"Queueing Flux Kontext Multi-image generation task for job {job.id}")
        app.send_task(
            'image_generation.tasks.generate_flux_kontext_multi',
            args=[str(job.id), webhook_url],
            countdown=2  # Small delay for connection stability
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating with Flux Kontext Multi-image: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Flux Kontext Multi-image generation job",
    responses={
        200: FluxKontextMultiStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_flux_kontext_multi_status(request, job_id):
    """
    Get the status of a Flux Kontext Multi-image generation job
    
    GET /api/images/generate/flux/kontext/multi-image/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(FluxKontextMultiJob, id=job_id)
        
        # Return the status
        serializer = FluxKontextMultiStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Flux Kontext Multi-image generation status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Flux Kontext Multi-image generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def flux_kontext_multi_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Flux Kontext Multi-image generation status updates
    
    POST /api/webhooks/flux/kontext/multi/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(FluxKontextMultiJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for Flux Kontext Multi-image job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"Flux Kontext Multi-image webhook received: {payload.get('status')} for {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for Flux Kontext Multi-image job {job_id}")
            return HttpResponse(status=400)
        
        # Process the webhook
        success = process_replicate_webhook(
            payload, 
            job, 
            job.client_webhook_url
        )
        
        if not success:
            logger.error(f"Failed to process webhook for Flux Kontext Multi-image job {job_id}")
            return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in flux_kontext_multi_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Flux Kontext Multi-image-list Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate images using Flux Kontext Multi-image-list model",
    request_body=FluxKontextMultiListInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=FluxKontextMultiListStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_flux_kontext_multi_list(request):
    """
    Generate images using Flux Kontext Multi-image-list model
    
    POST /api/images/generate/flux/kontext/multi-image-list/
    """
    serializer = FluxKontextMultiListInputSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"FluxKontextMultiListInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Generate webhook secret
        webhook_secret = secrets.token_urlsafe(32)
        
        # Create job in database
        job = FluxKontextMultiListJob.objects.create(
            prompt=serializer.validated_data['prompt'],
            input_images=serializer.validated_data['input_images'],
            seed=serializer.validated_data.get('seed'),
            aspect_ratio=serializer.validated_data.get('aspect_ratio', 'match_input_image'),
            output_format=serializer.validated_data.get('output_format', 'png'),
            safety_tolerance=serializer.validated_data.get('safety_tolerance', 2),
            webhook_secret=webhook_secret,
            webhook_events_filter=serializer.validated_data.get('webhook_events_filter', ['start', 'output', 'completed']),
            client_webhook_url=serializer.validated_data.get('client_webhook_url')
        )
        
        # Generate webhook URL for Replicate callbacks
        base_url = settings.WEBHOOK_BASE_URL
        webhook_path = reverse('image_generation:flux_kontext_multi_list_webhook', kwargs={
            'job_id': job.id,
            'secret': webhook_secret
        })
        webhook_url = urljoin(base_url, webhook_path)
        
        # Start the Celery task asynchronously
        app.send_task(
            'image_generation.tasks.generate_flux_kontext_multi_list',
            args=[str(job.id), webhook_url],
            countdown=0
        )
        
        # Return a 202 Accepted response with job info
        return Response({
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error generating with Flux Kontext Multi-image-list: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get the status of a Flux Kontext Multi-image-list generation job",
    responses={
        200: FluxKontextMultiListStatusSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['GET'])
def get_flux_kontext_multi_list_status(request, job_id):
    """
    Get the status of a Flux Kontext Multi-image-list generation job
    
    GET /api/images/generate/flux/kontext/multi-image-list/<job_id>/
    """
    try:
        # Get the job from database
        job = get_object_or_404(FluxKontextMultiListJob, id=job_id)
        
        # Return the status
        serializer = FluxKontextMultiListStatusSerializer(job)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error getting Flux Kontext Multi-image-list generation status: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send Flux Kontext Multi-image-list generation status updates",
    responses={
        200: "OK",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def flux_kontext_multi_list_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send Flux Kontext Multi-image-list generation status updates
    
    POST /api/webhooks/flux/kontext/multi-list/<job_id>/<secret>/
    """
    try:
        # Get the job
        job = get_object_or_404(FluxKontextMultiListJob, id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for job {job_id}")
            return HttpResponse(status=403)
            
        # Get the webhook payload
        try:
            payload = json.loads(request.body)
            logger.debug(f"Received webhook for job {job_id}: {request.body}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in webhook request for job {job_id}")
            return HttpResponse(status=400)
            
        # Handle the webhook
        status = payload.get('status')
        
        if status == 'succeeded':
            # Extract output URL
            output = payload.get('output', None)
            
            if output:
                if isinstance(output, list) and output:
                    job.output_url = output[0]
                elif isinstance(output, str):
                    job.output_url = output
                else:
                    logger.warning(f"Unexpected output format: {output}")
            
            job.status = 'succeeded'
            job.save(update_fields=['status', 'output_url'])
            
        elif status == 'failed':
            job.status = 'failed'
            job.error_message = payload.get('error', 'Unknown error')
            job.save(update_fields=['status', 'error_message'])
            
        # Notify client webhook if provided
        if job.client_webhook_url:
            try:
                client_payload = {
                    'status': job.status,
                    'job_id': str(job.id),
                    'timestamp': timezone.now().isoformat()
                }
                
                if job.output_url:
                    client_payload['output_url'] = job.output_url
                    
                if job.error_message:
                    client_payload['error'] = job.error_message
                    
                requests.post(job.client_webhook_url, json=client_payload, timeout=5)
                logger.info(f"Notified client webhook for job {job_id}")
            except Exception as e:
                logger.error(f"Error notifying client webhook for job {job_id}: {str(e)}")
                return HttpResponse(status=500)
        
        # Mark job as completed if successful
        if job.status == 'succeeded':
            job.completed_at = timezone.now()
            job.save(update_fields=['completed_at'])
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in flux_kontext_multi_list_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)


# Flux Kontext Portrait-Series Generation Views
@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Generate portrait series using Flux Kontext Portrait-Series model",
    request_body=FluxKontextPortraitSeriesInputSerializer,
    responses={
        202: openapi.Response(
            description="Accepted - Job submitted successfully",
            schema=FluxKontextPortraitSeriesStatusSerializer
        ),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['images']
)
@api_view(['POST'])
def generate_flux_kontext_portrait_series(request):
    """
    Generate portrait series using Flux Kontext Portrait-Series model
    """
    serializer = FluxKontextPortraitSeriesInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Generate a webhook secret for this job
    webhook_secret = generate_webhook_secret()
    
    # Create the job with input parameters
    job = FluxKontextPortraitSeriesJob.objects.create(
        input_image=data.get('input_image'),
        background=data.get('background', 'white'),
        num_images=data.get('num_images', 4),
        randomize_images=data.get('randomize_images', False),
        output_format=data.get('output_format', 'png'),
        safety_tolerance=data.get('safety_tolerance', 2),
        status='starting',
        webhook_secret=webhook_secret,
        client_webhook_url=data.get('client_webhook_url'),
        webhook_events_filter=data.get('webhook_events_filter', [])
    )
    
    # Generate a webhook URL for Replicate to call
    webhook_url = generate_webhook_url(
        view_name='image_generation:flux_kontext_portrait_series_webhook',
        job_id=str(job.id),
        secret=webhook_secret,
        request=request
    )
    
    # Schedule the task
    portrait_series_task.delay(str(job.id), webhook_url)
    
    # Create a serializer for the response
    response_serializer = FluxKontextPortraitSeriesStatusSerializer(job)
    return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)


@swagger_auto_schema(
    method='get',
    operation_description="Get status of a Flux Kontext Portrait-Series job",
    responses={
        200: openapi.Response(
            description="OK - Job details retrieved",
            schema=FluxKontextPortraitSeriesStatusSerializer
        ),
        404: "Not Found - Job not found"
    },
    tags=['images']
)
@api_view(['GET'])
def get_flux_kontext_portrait_series_status(request, job_id):
    """
    Get status of a Flux Kontext Portrait-Series job
    """
    try:
        job = FluxKontextPortraitSeriesJob.objects.get(id=job_id)
        serializer = FluxKontextPortraitSeriesStatusSerializer(job)
        return Response(serializer.data)
    except FluxKontextPortraitSeriesJob.DoesNotExist:
        return Response(
            {"error": f"Portrait-Series job {job_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@csrf_exempt
@api_view(['POST'])
def flux_kontext_portrait_series_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to update status of portrait-series jobs
    """
    try:
        # Get the job
        job = FluxKontextPortraitSeriesJob.objects.get(id=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            return Response(
                {"error": "Invalid webhook secret"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Process the webhook payload
        payload = request.data
        logger.info(f"Received webhook for portrait-series job {job_id}: {payload}")
        
        if process_replicate_webhook(payload, job, job.client_webhook_url):
            return Response({"status": "success"})
        else:
            return Response(
                {"error": "Failed to process webhook payload"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except FluxKontextPortraitSeriesJob.DoesNotExist:
        return Response(
            {"error": f"Portrait-Series job {job_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error processing portrait-series webhook: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def model_gallery(request):
    """
    View for the model gallery page that displays trained LoRA models
    """
    # You might want to fetch actual model data here from your database
    # For now, we'll just render the template
    return render(request, 'model_gallery.html', {
        'page_title': 'Model Gallery',
    })