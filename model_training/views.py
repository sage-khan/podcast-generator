from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
import logging
import traceback
import json
import uuid
from django.views.decorators.csrf import csrf_exempt
from model_training.models import (
    TrainedModel, TrainingImage, LoraTrainingJob
)
from model_training.serializers import (
    TrainedModelSerializer, TrainingImageSerializer,
    LoraTrainingInputSerializer,
    LoraTrainingOutputSerializer, ModelTrainSerializer
)

# Import Swagger documentation utilities
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import storage_client
from shared.utils.webhook_utils import (
    generate_webhook_secret, 
    generate_webhook_url, 
    validate_webhook_secret,
    process_replicate_webhook,
    send_client_webhook
)
from shared.utils.model_validation import (
    parse_replicate_model_id,
    validate_webhook_url,
    validate_replicate_model_version_field,
    generate_payload_for_replicate
)
from shared.utils.task_utils import queue_task

logger = logging.getLogger(__name__)

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Fine-tune a LoRA model",
    request_body=LoraTrainingInputSerializer,
    responses={
        201: openapi.Response(description="Created - Training job started", schema=LoraTrainingOutputSerializer),
        400: "Bad Request - Invalid input parameters",
        500: "Internal Server Error"
    },
    tags=['model-training']
)
@api_view(['POST'])
def finetune_lora(request):
    """
    Fine-tune a LoRA model

    POST /api/models/finetune/lora/
    """
    # Handle both original and new serializer formats for backward compatibility
    if 'name' in request.data and 'image_urls' in request.data:
        # Legacy format - map fields to new format
        serializer = ModelTrainSerializer(data=request.data)
        if serializer.is_valid():
            # Map legacy format to new format
            data = {
                'model_name': serializer.validated_data.get('name'),
                'input_image_urls': serializer.validated_data.get('image_urls'),
                'trigger_word': serializer.validated_data.get('trigger_word'),
                'seed': serializer.validated_data.get('seed'),
                'steps': serializer.validated_data.get('steps', 1000),
                'client_webhook_url': serializer.validated_data.get('client_webhook_url')
            }
            serializer = LoraTrainingInputSerializer(data=data)
    else:
        # New format
        serializer = LoraTrainingInputSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning(f"LoraTrainingInputSerializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get validated data
        data = serializer.validated_data
        
        # Generate a unique webhook secret
        webhook_secret = generate_webhook_secret()
        
        # Create a new training job
        training_job = LoraTrainingJob.objects.create(
            model_name=data.get('model_name'),
            trigger_word=data.get('trigger_word'),
            input_image_urls=data.get('input_image_urls'),
            seed=data.get('seed'),
            steps=data.get('steps', 1000),
            lora_rank=data.get('lora_rank', 4),
            resolution=data.get('resolution', 512),
            batch_size=data.get('batch_size', 1),
            learning_rate=data.get('learning_rate', 1e-4),
            status='starting',
            webhook_secret=webhook_secret,
            client_webhook_url=data.get('client_webhook_url')
        )
        
        # Generate webhook URL
        webhook_url = generate_webhook_url(
            'model_training:lora_webhook', 
            training_job.id, 
            webhook_secret, 
            request
        )
        
        # Store the webhook URL on the job
        training_job.webhook_url = webhook_url
        training_job.save()
        
        # Initialize the Replicate client
        client = ReplicateClient()
        
        # Start the training job asynchronously
        logger.info(f"Starting LoRA training job for {data.get('model_name')}...")
        
        # Queue the training task to be executed in the background
        try:
            task_id = queue_task(
                'model_training.tasks.start_lora_training',
                args=[
                    str(training_job.id),
                    data.get('input_image_urls'),
                    data.get('trigger_word'),
                    data.get('model_name'),
                    data.get('steps', 1000),
                    data.get('lora_rank', 4),
                    webhook_url                ],
                countdown=2  # Small delay for connection stability
            )
            
            logger.info(f"LoRA training task queued with ID: {task_id}")
            
            # Return the job data
            serializer = LoraTrainingOutputSerializer(training_job)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            # Handle error in task queueing
            training_job.status = 'failed'
            training_job.error_message = f"Failed to queue training task: {str(e)}"
            training_job.save()
            
            logger.error(f"Failed to queue LoRA training task: {str(e)}")
            return Response(
                {"error": "Failed to start LoRA training job", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error in finetune_lora: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@swagger_auto_schema(method='post',
    operation_description="Webhook endpoint for Replicate to send LoRA training status updates",
    responses={
        200: "OK - Webhook processed successfully",
        403: "Forbidden - Invalid webhook secret",
        500: "Internal Server Error"
    },
    tags=['model-training']
)
@api_view(['POST'])
def lora_webhook(request, job_id, secret):
    """
    Webhook endpoint for Replicate to send LoRA training status updates

    POST /api/webhooks/lora/{job_id}/{secret}/
    """
    try:
        # Get the LoraTrainingJob instance
        job = get_object_or_404(LoraTrainingJob, pk=job_id)
        
        # Validate the webhook secret
        if not validate_webhook_secret(secret, job.webhook_secret):
            logger.warning(f"Invalid webhook secret for LoRA job {job_id}")
            return HttpResponse(status=403)
        
        # Parse the request body
        try:
            payload = json.loads(request.body)
            logger.info(f"LoRA webhook received: {payload.get('status')} for job {job_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in webhook request body for LoRA job {job_id}")
            return HttpResponse(status=400)
        
        # Extract status from the webhook payload
        status = payload.get('status')
        output = payload.get('output', {})
        
        # Update job status based on webhook
        if status == 'succeeded':
            # For successful trainings, extract the model version
            if isinstance(output, dict) and 'version' in output:
                # Store the model version ID
                job.replicate_model_version = output.get('version')
                job.status = 'succeeded'
                job.completed_at = timezone.now()
                
                # Create or update a TrainedModel record
                model, created = TrainedModel.objects.get_or_create(
                    name=job.model_name,
                    defaults={
                        'trigger_word': job.trigger_word,
                        'replicate_owner': job.replicate_model_owner,
                        'replicate_model_name': job.model_name,
                        'replicate_model_version': job.replicate_model_version,
                        'training_images_urls': job.input_image_urls,
                        'steps': job.steps,
                        'lora_rank': job.lora_rank,
                        'resolution': job.resolution,
                        'batch_size': job.batch_size,
                        'learning_rate': job.learning_rate,
                        'status': 'completed',
                        'training_started_at': job.started_at,
                        'training_completed_at': job.completed_at
                    }
                )
                
                if not created:
                    # Update existing model
                    model.replicate_model_version = job.replicate_model_version
                    model.training_images_urls = job.input_image_urls
                    model.status = 'completed'
                    model.save()
                
                logger.info(f"LoRA training job {job_id} succeeded, model version: {job.replicate_model_version}")
            else:
                # Missing model version in output
                job.status = 'failed'
                job.error_message = "Model version missing from successful training output"
                logger.error(f"LoRA webhook missing version in output: {output}")
        
        elif status == 'failed':
            # Handle failed training
            job.status = 'failed'
            job.error_message = payload.get('error', 'Unknown error')
            job.completed_at = timezone.now()
            logger.error(f"LoRA training job {job_id} failed: {job.error_message}")
        
        elif status == 'processing':
            # Update the job to processing status if it was starting
            if job.status == 'starting':
                job.status = 'processing'
                job.started_at = timezone.now()
                logger.info(f"LoRA training job {job_id} is now processing")
            
            # If we get the training ID, store it
            if payload.get('id'):
                job.replicate_training_id = payload.get('id')
        
        # Save the job with updated info
        job.save()
        
        # Send client webhook if URL provided and job is completed (success or failure)
        if job.client_webhook_url and job.status in ['succeeded', 'failed']:
            client_payload = {
                'job_id': str(job.id),
                'status': job.status,
                'model_name': job.model_name
            }
            
            # Add relevant information based on status
            if job.status == 'succeeded':
                client_payload['model_version'] = job.replicate_model_version
                client_payload['model_id'] = f"{job.replicate_model_owner}/{job.model_name}:{job.replicate_model_version}"
            elif job.status == 'failed':
                client_payload['error_message'] = job.error_message
            
            # Send the notification
            send_client_webhook(job.client_webhook_url, client_payload)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error in lora_webhook: {str(e)}\n{traceback.format_exc()}")
        return HttpResponse(status=500)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get details of a specific LoRA training job",
    responses={
        200: LoraTrainingOutputSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['model-training']
)
@api_view(['GET'])
def lora_job_detail(request, job_id):
    """
    Get details of a specific LoRA training job

    GET /api/models/finetune/lora/{job_id}/
    """
    try:
        job = get_object_or_404(LoraTrainingJob, pk=job_id)
        serializer = LoraTrainingOutputSerializer(job)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error retrieving LoRA job {job_id}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@swagger_auto_schema(method='get',
    operation_description="Get status of a LoRA training job",
    responses={
        200: LoraTrainingOutputSerializer,
        404: "Not Found - Job does not exist",
        500: "Internal Server Error"
    },
    tags=['model-training']
)
@api_view(['GET'])
def get_lora_training_status(request, job_id):
    """
    Get status of a LoRA training job

    GET /api/models/finetune/lora/status/{job_id}/
    """
    try:
        job = get_object_or_404(LoraTrainingJob, pk=job_id)
        serializer = LoraTrainingOutputSerializer(job)
        return Response(serializer.data)
    except LoraTrainingJob.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error retrieving LoRA training status for job {job_id}: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainedModelViewSet(viewsets.ModelViewSet):
    """API endpoint for trained LoRA models"""
    queryset = TrainedModel.objects.all().order_by('-created_at')
    serializer_class = TrainedModelSerializer
    
    @swagger_auto_schema(
        operation_description="List or filter trained LoRA models",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by model status",
                type=openapi.TYPE_STRING,
                required=False,
                enum=['active', 'training', 'failed', 'archived']
            )
        ],
        responses={
            200: TrainedModelSerializer(many=True),
            400: "Bad Request"
        },
        tags=['model-training']
    )
    def get_queryset(self):
        queryset = TrainedModel.objects.all().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset