import logging
import os
import time
import json
import uuid
import requests
import replicate
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from shared.utils.task_utils import with_task_logging
from config.celery import app
from .models import Character, Pose, LoraGenerationJob, FluxUltraProJob, FluxKontextProJob, FluxKontextMultiJob, FluxKontextMultiListJob, FluxKontextPortraitSeriesJob
from shared.clients.storage_client import StorageClient

logger = logging.getLogger(__name__)

@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_character"
)
@with_task_logging
def generate_character(self, character_id, client_webhook_url=None):
    """
    Generate a character image using Replicate
    
    Args:
        character_id: ID of the Character
        client_webhook_url: Optional URL to notify when generation completes
    """
    logger.info(f"Starting character generation for character {character_id}")
    
    try:
        # Get the character
        character = Character.objects.get(id=character_id)
        
        # Mark as processing
        character.status = "processing"
        character.save(update_fields=["status"])
        
        # Generate webhook URL with secret
        base_url = settings.WEBHOOK_BASE_URL
        if not base_url.startswith('https://'):
            logger.warning(f"Webhook base URL {base_url} doesn't use HTTPS, which is required by Replicate")
            base_url = base_url.replace('http://', 'https://')
            
        # Create webhook URL with namespace
        webhook_path = reverse('image_generation:character_webhook', kwargs={
            'character_id': character.id, 
            'secret': character.webhook_secret
        })
        webhook_url = f"{base_url}{webhook_path}"
        
        # Prepare generation inputs
        generation_inputs = {
            "prompt": character.prompt,
            "negative_prompt": character.negative_prompt or "",
            "num_inference_steps": character.num_inference_steps or 30,
            "guidance_scale": character.guidance_scale or 7.5
        }
        
        # Start the generation
        logger.info(f"Starting Replicate generation with webhook: {webhook_url}")
        
        # Get model details from settings or use defaults
        model_id = settings.get('REPLICATE_CHARACTER_MODEL', 'stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316')
        model_parts = model_id.split(':')
        model = model_parts[0]
        version = model_parts[1] if len(model_parts) > 1 else None
        
        # Use predictions.create method
        prediction = replicate.predictions.create(
            model=model,
            version=version,
            input=generation_inputs,
            webhook=webhook_url,
            webhook_events_filter=["start", "output", "logs", "completed"]
        )
        
        # Update character with prediction ID
        character.replicate_prediction_id = prediction.id
        character.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Character generation {character_id} started with prediction ID: {prediction.id}")
        
        # Store the client webhook URL if provided
        if client_webhook_url:
            character.client_webhook_url = client_webhook_url
            character.save(update_fields=["client_webhook_url"])
            
            # Notify client of job start
            try:
                requests.post(
                    client_webhook_url,
                    json={
                        "status": "processing",
                        "character_id": str(character.id),
                        "message": "Character generation started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "character_id": str(character.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except Character.DoesNotExist:
        logger.error(f"Character {character_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error generating character {character_id}: {str(e)}")
        
        # Update character status if it exists
        try:
            character = Character.objects.get(id=character_id)
            character.status = "failed"
            character.error_message = str(e)
            character.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if client_webhook_url:
                try:
                    requests.post(
                        client_webhook_url,
                        json={
                            "status": "failed",
                            "character_id": str(character.id),
                            "message": f"Character generation failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except Character.DoesNotExist:
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_poses"
)
@with_task_logging
def generate_poses(self, pose_id, client_webhook_url=None):
    """
    Generate pose variations for a character using Replicate
    
    Args:
        pose_id: ID of the Pose
        client_webhook_url: Optional URL to notify when generation completes
    """
    logger.info(f"Starting pose generation for pose {pose_id}")
    
    try:
        # Get the pose
        pose = Pose.objects.get(id=pose_id)
        
        # Mark as processing
        pose.status = "processing"
        pose.save(update_fields=["status"])
        
        # Generate webhook URL with secret
        base_url = settings.WEBHOOK_BASE_URL
        if not base_url.startswith('https://'):
            logger.warning(f"Webhook base URL {base_url} doesn't use HTTPS, which is required by Replicate")
            base_url = base_url.replace('http://', 'https://')
            
        # Create webhook URL with namespace
        webhook_path = reverse('image_generation:pose_webhook', kwargs={
            'pose_id': pose.id, 
            'secret': pose.webhook_secret
        })
        webhook_url = f"{base_url}{webhook_path}"
        
        # Prepare generation inputs
        generation_inputs = {
            "prompt": pose.prompt,
            "negative_prompt": pose.negative_prompt or "",
            "num_outputs": pose.num_outputs or 4,
            "guidance_scale": pose.guidance_scale or 7.5,
            "controlnet_conditioning_scale": pose.controlnet_scale or 0.8
        }
        
        if pose.reference_image_url:
            generation_inputs["reference_image"] = pose.reference_image_url
        
        # Start the generation
        logger.info(f"Starting Replicate pose generation with webhook: {webhook_url}")
        
        # Get model details from settings or use defaults
        model_id = settings.get('REPLICATE_POSE_MODEL', 'stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316')
        model_parts = model_id.split(':')
        model = model_parts[0]
        version = model_parts[1] if len(model_parts) > 1 else None
        
        # Use predictions.create method
        prediction = replicate.predictions.create(
            model=model,
            version=version,
            input=generation_inputs,
            webhook=webhook_url,
            webhook_events_filter=["start", "output", "logs", "completed"]
        )
        
        # Update pose with prediction ID
        pose.replicate_prediction_id = prediction.id
        pose.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Pose generation {pose_id} started with prediction ID: {prediction.id}")
        
        # Store the client webhook URL if provided
        if client_webhook_url:
            pose.client_webhook_url = client_webhook_url
            pose.save(update_fields=["client_webhook_url"])
            
            # Notify client of job start
            try:
                requests.post(
                    client_webhook_url,
                    json={
                        "status": "processing",
                        "pose_id": str(pose.id),
                        "message": "Pose generation started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "pose_id": str(pose.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except Pose.DoesNotExist:
        logger.error(f"Pose {pose_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error generating pose {pose_id}: {str(e)}")
        
        # Update pose status if it exists
        try:
            pose = Pose.objects.get(id=pose_id)
            pose.status = "failed"
            pose.error_message = str(e)
            pose.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if client_webhook_url:
                try:
                    requests.post(
                        client_webhook_url,
                        json={
                            "status": "failed",
                            "pose_id": str(pose.id),
                            "message": f"Pose generation failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except Pose.DoesNotExist:
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(bind=True, max_retries=3, retry_backoff=True)
@with_task_logging
def generate_with_lora(self, job_id, webhook_url):
    """
    Generate images using a LoRA model via Replicate
    
    Args:
        job_id: ID of the LoraGenerationJob
        webhook_url: URL for Replicate to send status updates
    """
    try:
        # Get the job from database
        job = LoraGenerationJob.objects.get(id=job_id)
        
        # If already completed or failed, don't restart
        if job.status in ['succeeded', 'failed', 'canceled']:
            logger.info(f"LoRA generation job {job_id} already in status {job.status}, skipping")
            return {"status": job.status, "id": str(job.id)}
        
        # Update status
        job.status = 'processing'
        job.save(update_fields=["status"])

        # Prepare the input parameters for Replicate API
        input_params = {
            "prompt": job.prompt,
            "negative_prompt": job.negative_prompt if job.negative_prompt else "",
            "num_outputs": job.num_outputs,
            "output_format": job.output_format,
            "output_quality": job.output_quality,
            "guidance_scale": job.guidance_scale,
            "num_inference_steps": job.num_inference_steps,
            "prompt_strength": job.prompt_strength,
            "aspect_ratio": job.aspect_ratio if job.aspect_ratio else "1:1",
            "lora_scale": job.lora_scale,
            # Add model parameter
            "model": job.model if hasattr(job, 'model') and job.model else "dev",
        }
       
        if input_params["aspect_ratio"] == "custom":
            # For custom aspect ratio, use width and height parameters with defaults of 512
            width = job.width if job.width else 512
            height = job.height if job.height else 512
            input_params["width"] = width
            input_params["height"] = height
            logger.info(f"Using custom dimensions: width={width}, height={height}")
        
        # Add optional parameters if they exist
        if job.seed is not None:
            input_params["seed"] = job.seed
            
        if hasattr(job, 'disable_safety_checker') and job.disable_safety_checker:
            input_params["disable_safety_checker"] = True
            
        if hasattr(job, 'image') and job.image:
            input_params["image"] = job.image
            
        if hasattr(job, 'mask') and job.mask:
            input_params["mask"] = job.mask
            
        if hasattr(job, 'extra_lora') and job.extra_lora:
            input_params["extra_lora"] = job.extra_lora
            
        if job.go_fast:
            input_params["go_fast"] = job.go_fast
            
        if job.megapixels:
            input_params["megapixels"] = job.megapixels
            
        if job.extra_lora_scale is not None:
            input_params["extra_lora_scale"] = job.extra_lora_scale
        
        logger.info(f"Starting LoRA generation job {job_id} with model: {job.model_id}")
        logger.debug(f"Input parameters: {json.dumps(input_params)}")
        
        # Initialize Replicate API
        import replicate
        
        # Make the prediction call using the full model ID
        prediction = replicate.predictions.create(
            version=job.model_id,  # Use the full model ID string
            input=input_params,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter
        )
        
        # Store the webhook events filter that was actually used
        job.webhook_events_filter_used = job.webhook_events_filter
        
        # Update job with prediction ID
        job.replicate_prediction_id = prediction.id
        job.save(update_fields=["replicate_prediction_id", "webhook_events_filter_used"])
        
        logger.info(f"Started LoRA generation job {job_id} with prediction ID: {prediction.id}")
        
        # Notify client via webhook if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "LoRA generation job started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except LoraGenerationJob.DoesNotExist:
        logger.error(f"LoRA generation job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting LoRA generation job {job_id}: {str(e)}")
        
        # Update job status if it exists
        try:
            job = LoraGenerationJob.objects.get(id=job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"LoRA generation job failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except LoraGenerationJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise

@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_flux_ultrapro"
)
@with_task_logging
def generate_flux_ultrapro(self, job_id, webhook_url):
    """
    Generate an image using Flux-1.1-UltraPro model via Replicate
    
    Args:
        job_id: ID of the FluxUltraProJob
        webhook_url: URL for Replicate to send status updates
    """
    logger.info(f"Starting Flux UltraPro generation for job {job_id}")
    
    try:
        # Get the job
        job = FluxUltraProJob.objects.get(id=job_id)
        
        # Mark as processing
        job.status = "processing"
        job.save(update_fields=["status"])
        
        # Prepare generation inputs
        input_params = {
            "prompt": job.prompt,
        }
        
        # Add optional parameters if provided
        if job.negative_prompt:
            input_params["negative_prompt"] = job.negative_prompt
        
        if job.seed is not None:
            input_params["seed"] = job.seed
            
        if job.aspect_ratio:
            input_params["aspect_ratio"] = job.aspect_ratio
            
        if job.image_prompt:
            input_params["image_prompt"] = job.image_prompt
            
        if job.output_format:
            input_params["output_format"] = job.output_format
            
        if job.safety_tolerance is not None:
            input_params["safety_tolerance"] = job.safety_tolerance
            
        if job.image_prompt_strength is not None:
            input_params["image_prompt_strength"] = job.image_prompt_strength
            
        if job.raw is not None:
            input_params["raw"] = job.raw
        
        logger.info(f"Starting Flux UltraPro job {job_id}")
        logger.debug(f"Input parameters: {json.dumps(input_params)}")
        
        # Initialize Replicate API
        # Use the model ID from documentation: blackforestlabs/flux-1-1-ultrapro
        prediction = replicate.predictions.create(
            version="blackforestlabs/flux-1-1-ultrapro:9b505b156eec233fc2ddc7cdad0dc26c6f6e51b2121dfa1ec70594b5f3d20a63", 
            input=input_params,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter or ["start", "output", "completed"]
        )
        
        # Update job with prediction ID
        job.replicate_prediction_id = prediction.id
        job.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Started Flux UltraPro job {job_id} with prediction ID: {prediction.id}")
        
        # Notify client via webhook if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "Flux UltraPro job started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except FluxUltraProJob.DoesNotExist:
        logger.error(f"Flux UltraPro job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting Flux UltraPro job {job_id}: {str(e)}")
        
        # Update job status if it exists
        try:
            job = FluxUltraProJob.objects.get(id=job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"Flux UltraPro job failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except FluxUltraProJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_flux_kontextpro"
)
@with_task_logging
def generate_flux_kontextpro(self, job_id, webhook_url):
    """
    Generate an image using Flux Kontext Pro model via Replicate
    
    Args:
        job_id: ID of the FluxKontextProJob
        webhook_url: URL for Replicate to send status updates
    """
    logger.info(f"Starting Flux Kontext Pro generation for job {job_id}")
    
    try:
        # Get the job
        job = FluxKontextProJob.objects.get(id=job_id)
        
        # Mark as processing
        job.status = "processing"
        job.save(update_fields=["status"])
        
        # Prepare generation inputs
        input_params = {
            "prompt": job.prompt,
            "input_image": job.input_image
        }
        
        # Add optional parameters if provided
        if job.seed is not None:
            input_params["seed"] = job.seed
            
        if job.aspect_ratio:
            input_params["aspect_ratio"] = job.aspect_ratio
            
        if job.output_format:
            input_params["output_format"] = job.output_format
            
        if job.safety_tolerance is not None:
            input_params["safety_tolerance"] = job.safety_tolerance
        
        logger.info(f"Starting Flux Kontext Pro job {job_id}")
        logger.debug(f"Input parameters: {json.dumps(input_params)}")
        
        # Initialize Replicate API
        # Use the model ID from documentation: blackforestlabs/flux-kontext-pro
        prediction = replicate.predictions.create(
            version="black-forest-labs/flux-kontext-pro", 
            input=input_params,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter or ["start", "output", "completed"]
        )
        
        # Update job with prediction ID
        job.replicate_prediction_id = prediction.id
        job.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Started Flux Kontext Pro job {job_id} with prediction ID: {prediction.id}")
        
        # Notify client via webhook if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "Flux Kontext Pro job started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except FluxKontextProJob.DoesNotExist:
        logger.error(f"Flux Kontext Pro job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting Flux Kontext Pro job {job_id}: {str(e)}")
        
        # Update job status if it exists
        try:
            job = FluxKontextProJob.objects.get(id=job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"Flux Kontext Pro job failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except FluxKontextProJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_flux_kontext_multi"
)
@with_task_logging
def generate_flux_kontext_multi(self, job_id, webhook_url):
    """
    Generate an image using Flux Kontext Multi-image model via Replicate
    
    Args:
        job_id: ID of the FluxKontextMultiJob
        webhook_url: URL for Replicate to send status updates
    """
    logger.info(f"Starting Flux Kontext Multi-image generation for job {job_id}")
    
    try:
        # Get the job
        job = FluxKontextMultiJob.objects.get(id=job_id)
        
        # Mark as processing
        job.status = "processing"
        job.save(update_fields=["status"])
        
        # Prepare generation inputs
        input_params = {
            "prompt": job.prompt,
            "input_image_1": job.input_image_1,
            "input_image_2": job.input_image_2
        }
        
        # Add optional parameters if provided
        if job.seed is not None:
            input_params["seed"] = job.seed
            
        if job.aspect_ratio:
            input_params["aspect_ratio"] = job.aspect_ratio
            
        if job.output_format:
            input_params["output_format"] = job.output_format
            
        if job.safety_tolerance is not None:
            input_params["safety_tolerance"] = job.safety_tolerance
        
        logger.info(f"Starting Flux Kontext Multi-image job {job_id}")
        logger.debug(f"Input parameters: {json.dumps(input_params)}")
        
        # Initialize Replicate API
        # Use the model ID from documentation: flux-kontext-apps/multi-image-kontext-max
        prediction = replicate.predictions.create(
            version="flux-kontext-apps/multi-image-kontext-max",
            input=input_params,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter or ["start", "output", "completed"]
        )
        
        # Update job with prediction ID
        job.replicate_prediction_id = prediction.id
        job.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Started Flux Kontext Multi-image job {job_id} with prediction ID: {prediction.id}")
        
        # Notify client via webhook if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "Flux Kontext Multi-image job started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except FluxKontextMultiJob.DoesNotExist:
        logger.error(f"Flux Kontext Multi-image job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting Flux Kontext Multi-image job {job_id}: {str(e)}")
        
        # Update job status if it exists
        try:
            job = FluxKontextMultiJob.objects.get(id=job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"Flux Kontext Multi-image job failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except FluxKontextMultiJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_flux_kontext_multi_list"
)
@with_task_logging
def generate_flux_kontext_multi_list(self, job_id, webhook_url):
    """
    Generate an image using Flux Kontext Multi-image-list model via Replicate
    
    Args:
        job_id: ID of the FluxKontextMultiListJob
        webhook_url: URL for Replicate to send status updates
    """
    try:
        # Get the job from the database
        job = FluxKontextMultiListJob.objects.get(id=job_id)
        
        # Mark as processing
        job.status = "processing"
        job.save(update_fields=["status"])
        
        # Store webhook URL
        job.webhook_url = webhook_url
        job.save(update_fields=["webhook_url"])
        
        # Prepare generation inputs
        input_params = {
            "prompt": job.prompt,
            "input_images": job.input_images
        }
        
        # Add optional parameters if provided
        if job.seed is not None:
            input_params["seed"] = job.seed
            
        if job.aspect_ratio:
            input_params["aspect_ratio"] = job.aspect_ratio
            
        if job.output_format:
            input_params["output_format"] = job.output_format
            
        if job.safety_tolerance is not None:
            input_params["safety_tolerance"] = job.safety_tolerance
        
        logger.info(f"Starting Flux Kontext Multi-image-list job {job_id}")
        logger.debug(f"Input parameters: {json.dumps(input_params)}")
        
        # Initialize Replicate API
        # Use the model name as the version as specified in the documentation
        prediction = replicate.predictions.create(
            version="flux-kontext-apps/multi-image-list",
            input=input_params,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter or ["start", "output", "completed"]
        )
        
        # Update job with prediction ID
        job.replicate_prediction_id = prediction.id
        job.save(update_fields=["replicate_prediction_id"])
        
        logger.info(f"Started Flux Kontext Multi-image-list job {job_id} with prediction ID: {prediction.id}")
        
        # Notify client via webhook if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "Flux Kontext Multi-image-list job started",
                        "replicate_id": prediction.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except FluxKontextMultiListJob.DoesNotExist:
        logger.error(f"Flux Kontext Multi-image-list job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting Flux Kontext Multi-image-list job {job_id}: {str(e)}")
        
        # Update job status if it exists
        try:
            job = FluxKontextMultiListJob.objects.get(id=job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"Flux Kontext Multi-image-list job failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except FluxKontextMultiListJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise


@app.task(
    bind=True,
    max_retries=5,
    retry_backoff=True,
    rate_limit="10/m",
    name="image_generation.tasks.generate_flux_kontext_portrait_series"
)
@with_task_logging
def generate_flux_kontext_portrait_series(self, job_id, webhook_url):
    """
    Generate portrait series using Flux Kontext portrait-series model via Replicate
    
    Args:
        job_id: ID of the FluxKontextPortraitSeriesJob
        webhook_url: URL for Replicate to send status updates
    """
    logger.info(f"Starting Flux Kontext Portrait-Series generation for job {job_id}")
    
    try:
        # Get the job
        job = FluxKontextPortraitSeriesJob.objects.get(id=job_id)
        
        # Mark as processing
        job.status = 'processing'
        job.save(update_fields=['status'])
        
        # Handle DigitalOcean Spaces URLs - they may not be directly accessible by Replicate
        input_image_url = job.input_image
        
        # Initialize storage client for handling DO Spaces URLs
        storage_client = StorageClient()
        
        # Check if the input_image URL is from DO Spaces and make it accessible
        if 'digitaloceanspaces.com' in input_image_url:
            try:
                logger.info(f"Converting DO Spaces URL to publicly accessible URL: {input_image_url}")
                # Try to get an accessible URL (presigned URL or public URL)
                input_image_url = storage_client.get_accessible_url(input_image_url)
                
                # If DO Spaces URLs are still problematic, we could download and upload to a temporary file service
                # This would be implemented here if needed based on production experience
                
            except Exception as storage_err:
                logger.error(f"Error making input image accessible: {str(storage_err)}")
                job.status = 'failed'
                job.error_message = f"Failed to access input image: {str(storage_err)}"
                job.save(update_fields=['status', 'error_message'])
                return
        
        # Format prediction inputs
        inputs = {
            "input_image": input_image_url,
            "background": job.background,
            "num_images": job.num_images,
            "output_format": job.output_format,
            "safety_tolerance": job.safety_tolerance
        }
        
        # Only include randomize_images if it's True (following the model's schema expectations)
        if job.randomize_images:
            inputs["randomize_images"] = True
        
        # Create a prediction on Replicate
        logger.info(f"Creating prediction with Flux Kontext Portrait-Series for job {job_id}")
        prediction = replicate.predictions.create(
            version="flux-kontext-apps/portrait-series",
            input=inputs,
            webhook=webhook_url,
            webhook_events_filter=job.webhook_events_filter if job.webhook_events_filter else None
        )
        
        # Store prediction ID and URL
        job.replicate_id = prediction.id
        job.replicate_url = prediction.urls.get("get")
        job.webhook_events_filter_used = job.webhook_events_filter
        job.save(update_fields=['replicate_id', 'replicate_url', 'webhook_events_filter_used'])
        
        # Notify client webhook of job start if provided
        if job.client_webhook_url:
            try:
                requests.post(
                    job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(job.id),
                        "message": "Portrait-Series generation started",
                        "replicate_id": prediction.id,
                        "replicate_url": prediction.urls.get("get"),
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(job.id),
            "status": "processing",
            "replicate_id": prediction.id
        }
        
    except FluxKontextPortraitSeriesJob.DoesNotExist:
        logger.error(f"Portrait-Series generation job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error in Flux Kontext Portrait-Series generation: {str(e)}")
        
        try:
            # Update job status to failed
            job = FluxKontextPortraitSeriesJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            
            # Notify client webhook of failure if provided
            if job.client_webhook_url:
                try:
                    requests.post(
                        job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(job.id),
                            "message": f"Portrait-Series generation failed: {str(e)}",
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except FluxKontextPortraitSeriesJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise