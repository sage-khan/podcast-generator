import logging
import traceback
from datetime import timedelta
from django.utils import timezone
import uuid
import os
import tempfile

import replicate
from django.db import transaction
from celery import shared_task
from urllib.parse import urlparse

from video_generation.models import KlingVideoJob, KlingLipsyncJob, GoogleVeo3VideoJob
from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import storage_client
from shared.utils.webhook_utils import send_client_webhook

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2)
def generate_kling_video(self, job_id, webhook_url=None):
    """
    Generate a video using the Kling v1.6 Pro model
    
    Args:
        job_id (str): UUID of the KlingVideoJob
        webhook_url (str, optional): Webhook URL to receive updates
    """
    logger.info(f"Starting Kling video generation for job {job_id}")
    
    try:
        # Get the video job
        job = KlingVideoJob.objects.get(id=job_id)
        
        # Update status to processing
        job.status = 'processing'
        job.save(update_fields=['status'])
        
        if job.client_webhook_url:
            # Send initial webhook to client
            send_client_webhook(job.client_webhook_url, {
                'id': str(job.id),
                'status': job.status,
            })
        
        # Create the input dictionary for Replicate
        input_dict = {
            'prompt': job.prompt,
            'aspect_ratio': job.aspect_ratio,
            'duration': job.duration,
            'cfg_scale': job.cfg_scale,
        }
        
        if job.negative_prompt:
            input_dict['negative_prompt'] = job.negative_prompt
            
        if job.start_image:
            # Ensure the start_image is accessible to external APIs
            input_dict['start_image'] = storage_client.get_accessible_url(job.start_image, expires_in=3600)
            
        if job.end_image:
            # Ensure the end_image is accessible to external APIs
            input_dict['end_image'] = storage_client.get_accessible_url(job.end_image, expires_in=3600)
            
        if job.reference_images and len(job.reference_images) > 0:
            # The model accepts up to 4 reference images
            valid_references = job.reference_images[:4]
            # Ensure all reference images are accessible to external APIs
            accessible_references = []
            for ref_img in valid_references:
                accessible_references.append(storage_client.get_accessible_url(ref_img, expires_in=3600))
            input_dict['reference_images'] = accessible_references
        
        # Initialize Replicate client
        replicate_client = ReplicateClient()
        
        # Get the model version (using the kwaivgi/kling-v1.6-pro model)
        model = "kwaivgi/kling-v1.6-pro"
        
        # Define webhook events filter
        webhook_events_filter = ["completed", "start", "output", "logs"]
        
        # Remove webhook parameters from input dict if they were added
        if 'webhook' in input_dict:
            del input_dict['webhook']
        if 'webhook_events_filter' in input_dict:
            del input_dict['webhook_events_filter']
        
        # Run the prediction with webhook URL if provided
        logger.info(f"Running Replicate prediction for job {job_id} with webhook URL: {webhook_url}")
        prediction = replicate_client.client.predictions.create(
            version=model,
            input=input_dict,
            webhook=webhook_url,
            webhook_events_filter=webhook_events_filter if webhook_url else None
        )
        
        # Store the Replicate URL
        replicate_id = prediction.id
        replicate_url = f"https://replicate.com/p/{replicate_id}"
        job.replicate_url = replicate_url
        job.save(update_fields=['replicate_url'])
        
        logger.info(f"Replicate prediction started for job {job_id}, URL: {replicate_url}")
        
        # If no webhook is provided, wait for the prediction to complete
        if not webhook_url:
            # Wait for the prediction to complete
            video_url = prediction.wait()
            
            # Store the output URL
            job.output_url = video_url
            job.status = 'succeeded'
            job.completed_at = timezone.now()
            job.save(update_fields=['output_url', 'status', 'completed_at'])
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'output_url': job.output_url,
                })
                
            logger.info(f"Kling video generation completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in generate_kling_video: {str(e)}\n{traceback.format_exc()}")
        
        try:
            # Update job status to failed
            job = KlingVideoJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'error': str(e),
                })
                
        except Exception as inner_e:
            logger.error(f"Error updating job status: {str(inner_e)}")
        
        # Re-raise the exception for Celery retry
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2)
def generate_kling_lipsync(self, job_id, webhook_url=None):
    """
    Generate lip-sync video using Kling's API through Replicate.
    
    This task performs the following steps:
    1. Fetches the job details from the database
    2. Downloads audio and video content locally
    3. Calls the Replicate API with proper parameters
    4. Updates the job with the results
    5. Cleans up any temporary files
    """
    logger.info(f"Starting Kling lipsync task for job {job_id}")
    
    # Initialize cleanup values
    replicate_prediction = None
    
    # Initialize temp file paths to None for proper cleanup in finally block
    temp_audio_path = None
    temp_video_path = None
    audio_file_handle = None
    video_file_handle = None
    
    try:
        # Get the lip-sync job
        job = KlingLipsyncJob.objects.get(id=job_id)
        
        # Update status to processing
        job.status = 'processing'
        job.save(update_fields=['status'])
        
        # Create the input dictionary for Replicate
        input_dict = {}
        
        # Handle audio as a local file input (Option 2): download and pass file handle
        if job.audio_file:
            logger.info(f"Downloading audio file for replicate upload: {job.audio_file}")
            download_attempts = 0
            max_attempts = 3
            
            while download_attempts < max_attempts:
                try:
                    download_attempts += 1
                    temp_audio_path = storage_client.download_file(job.audio_file)
                    
                    # Verify the file exists and has content
                    if os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
                        logger.debug(f"Downloaded audio successfully to: {temp_audio_path} (Size: {os.path.getsize(temp_audio_path)} bytes)")
                        audio_file_handle = open(temp_audio_path, 'rb')
                        input_dict['audio_file'] = audio_file_handle
                        break
                    else:
                        logger.warning(f"Downloaded file exists={os.path.exists(temp_audio_path)}, but size is 0 or file not found. Retrying ({download_attempts}/{max_attempts})")
                        if download_attempts >= max_attempts:
                            raise FileNotFoundError(f"Downloaded audio file is empty or not found: {temp_audio_path}")
                except Exception as e:
                    if download_attempts >= max_attempts:
                        logger.error(f"Failed to download audio after {max_attempts} attempts: {str(e)}")
                        logger.error(f"Falling back to presigned URL for audio_file")
                        presigned_audio_url = storage_client.get_accessible_url(job.audio_file, expires_in=3600)
                        logger.debug(f"Generated presigned audio URL: {presigned_audio_url}")
                        input_dict['audio_file'] = presigned_audio_url
                    else:
                        logger.warning(f"Download attempt {download_attempts} failed: {str(e)}. Retrying...")
        
        # Then handle the video file - provide the URL directly (Replicate expects 'video_url')
        if job.video_url:
            logger.info(f"Processing video URL: {job.video_url}")
            presigned_video_url = storage_client.get_accessible_url(job.video_url, expires_in=3600)
            logger.debug(f"Generated presigned video URL: {presigned_video_url}")
            
            # Replicate model requires the parameter name 'video_url'
            input_dict['video_url'] = presigned_video_url
        
        # Set up the rest of the parameters for the API call
        if job.prompt:
            input_dict['prompt'] = job.prompt
        
        if job.negative_prompt:
            input_dict['negative_prompt'] = job.negative_prompt
        
        # Initialize Replicate client
        replicate_client = ReplicateClient()
        
        # Get the model version (using the kwaivgi/kling-lip-sync model)
        model = "kwaivgi/kling-lip-sync"
        
        # Define webhook events filter
        webhook_events_filter = ["completed", "start", "output", "logs"]
        
        # Remove webhook parameters from input dict if they were added
        if 'webhook' in input_dict:
            del input_dict['webhook']
        if 'webhook_events_filter' in input_dict:
            del input_dict['webhook_events_filter']
        
        # Log sanitized input parameters for easier debugging (avoid dumping binary data)
        import json as _json
        sanitized_input = {k: ("<file_handle>" if not isinstance(v, (str, int, float, bool, type(None))) else v) for k, v in input_dict.items()}
        logger.info(f"Replicate input payload: {_json.dumps(sanitized_input, indent=2)}")
        
        logger.info(f"Running Replicate prediction for job {job_id}")
        logger.info(f"Input parameters: {', '.join(input_dict.keys())}")
        
        prediction = replicate_client.client.predictions.create(
            version=model,
            input=input_dict,
            webhook=webhook_url,
            webhook_events_filter=webhook_events_filter if webhook_url else None
        )
        
        # Store the Replicate URL
        replicate_id = prediction.id
        replicate_url = f"https://replicate.com/p/{replicate_id}"
        job.replicate_url = replicate_url
        job.save(update_fields=['replicate_url'])
        
        logger.info(f"Replicate prediction started for job {job_id}, URL: {replicate_url}")
        
        # If no webhook is provided, wait for the prediction to complete
        if not webhook_url:
            # Wait for the prediction to complete
            video_url = prediction.wait()
            
            # Store the output URL
            job.output_url = video_url
            job.status = 'succeeded'
            job.completed_at = timezone.now()
            job.save(update_fields=['output_url', 'status', 'completed_at'])
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'output_url': job.output_url,
                })
                
            logger.info(f"Kling lip-sync completed for job {job_id}")
        
    except Exception as e:
        error_msg = f"Failed to generate Kling lip-sync: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        try:
            # Update job status to failed
            job = KlingLipsyncJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'error': str(e),
                })
        except Exception as e2:
            logger.error(f"Error updating job status: {str(e2)}")
    finally:
        # Close file handles if they were opened
        try:
            if audio_file_handle:
                audio_file_handle.close()
                logger.debug(f"Closed audio file handle for {temp_audio_path}")
        except Exception as e:
            logger.warning(f"Error closing audio file handle: {str(e)}")
        
        # Cleanup temporary files
        try:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                logger.debug(f"Cleaned up temporary audio file: {temp_audio_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary audio file {temp_audio_path}: {str(e)}")


@shared_task(bind=True, max_retries=2)
def generate_google_veo3_video(self, job_id, webhook_url=None):
    """
    Generate a video using Google's Veo-3 model via Replicate API
    
    Args:
        job_id (str): ID of the GoogleVeo3VideoJob
        webhook_url (str, optional): URL for Replicate to send webhook updates
    """
    logger.info(f"Starting Google Veo 3 video generation for job {job_id}")
    
    # Webhook events we want to receive
    webhook_events_filter = ["start", "output", "completed"]
    
    # Get the job from database
    try:
        job = GoogleVeo3VideoJob.objects.get(id=job_id)
    except GoogleVeo3VideoJob.DoesNotExist:
        logger.error(f"GoogleVeo3VideoJob {job_id} not found")
        return
    
    # Mark the job as processing
    job.status = "processing"
    job.save(update_fields=['status'])
    
    # Create Replicate client
    replicate_client = ReplicateClient()
    
    try:
        # Model version from documentation
        model = "google/veo-3"
        
        # Prepare input for Google Veo-3 model
        input_dict = {
            "prompt": job.prompt,
            "enhance_prompt": job.enhance_prompt
        }
        
        # Add optional parameters only if they are set
        if job.negative_prompt and job.negative_prompt.strip():
            input_dict["negative_prompt"] = job.negative_prompt
        
        if job.seed is not None:
            input_dict["seed"] = job.seed
        
        logger.info(f"Sending request to Google Veo-3 model with input: {input_dict}")
        
        # Create the prediction on Replicate
        prediction = replicate_client.client.predictions.create(
            version=model,
            input=input_dict,
            webhook=webhook_url,
            webhook_events_filter=webhook_events_filter if webhook_url else None
        )
        
        # Store Replicate URL
        job.replicate_url = f"https://replicate.com/p/{prediction.id}"
        job.save(update_fields=['replicate_url'])
        
        # If no webhook is provided, wait for the prediction to finish
        if not webhook_url:
            prediction = replicate_client.client.predictions.wait(prediction.id)
            
            # Update job with prediction output
            if prediction.status == "succeeded":
                output_url = prediction.output
                
                # Update job status
                job.status = "succeeded"
                job.output_url = output_url
                job.video_url = output_url  # Set video_url to the same URL for frontend compatibility
                job.completed_at = timezone.now()
                job.save(update_fields=['status', 'output_url', 'video_url', 'completed_at'])
                
                logger.info(f"Google Veo-3 video generation completed for job {job_id}")
                
            else:
                # Update job status
                job.status = "failed"
                job.error_message = f"Replicate prediction failed: {prediction.error}"
                job.save(update_fields=['status', 'error_message'])
                
                logger.error(f"Google Veo-3 video generation failed for job {job_id}: {prediction.error}")
        
    except Exception as e:
        error_message = f"Error in generate_google_veo3_video task: {str(e)}"
        logger.error(f"{error_message}\n{traceback.format_exc()}")
        
        # Update job status
        job.status = "failed"
        job.error_message = error_message
        job.save(update_fields=['status', 'error_message'])
        
        # Retry the task if appropriate
        max_retries = self.max_retries
        if self.request.retries < max_retries:
            logger.info(f"Retrying generate_google_veo3_video task for job {job_id}. Attempt {self.request.retries + 1} of {max_retries + 1}")
            raise self.retry(exc=e, countdown=5)
