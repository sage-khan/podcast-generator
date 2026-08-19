import logging
import os
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests

from django.conf import settings
from celery import shared_task

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import StorageClient
from shared.utils.webhook_utils import send_client_webhook
from shared.utils.webhook_utils import generate_client_webhook_notification

logger = logging.getLogger(__name__)

def create_retry_session(retries=3, backoff_factor=0.5, 
                         status_forcelist=(500, 502, 503, 504),
                         allowed_methods=None):
    """Create a requests session with retry capabilities for better reliability
    in Docker/containerized environments.
    
    Args:
        retries: Number of times to retry the request
        backoff_factor: A backoff factor to apply between attempts
        status_forcelist: HTTP status codes that we should force a retry on
        allowed_methods: HTTP methods that should retry on failure
        
    Returns:
        A configured requests.Session object with retry capabilities
    """
    allowed_methods = allowed_methods or ["HEAD", "GET", "PUT", "POST", "PATCH"]
    
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
    )
    
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def start_lora_training(self, 
                        job_id, 
                        model_name, 
                        training_image_urls, 
                        class_word, 
                        instance_prompt, 
                        num_training_steps=1000, 
                        learning_rate=1e-4,
                        webhook_url=None, 
                        client_webhook_url=None):
    """Start a LoRA training job on Replicate and update the database with results.
    
    Args:
        job_id: The ID of the LoraTrainingJob to update
        model_name: Name of the model being trained
        training_image_urls: List of URLs to training images
        class_word: The class word for the model (e.g., "person", "character")
        instance_prompt: The instance prompt including the token to train
        num_training_steps: Number of training steps
        learning_rate: Learning rate for training
        webhook_url: Webhook URL for Replicate to send updates to
        client_webhook_url: Optional webhook URL to notify client of updates
    
    Returns:
        Dictionary with training job information
    """
    try:
        # Add a small delay to ensure Redis connection is stable (for containerized environments)
        time.sleep(2)
        
        logger.info(f"Starting LoRA training for job {job_id} with {len(training_image_urls)} images")
        
        # Import here to avoid circular imports
        from model_training.models import LoraTrainingJob
        
        # Get training job
        try:
            training_job = LoraTrainingJob.objects.get(id=job_id)
            training_job.status = "processing"
            training_job.save()
        except LoraTrainingJob.DoesNotExist:
            logger.error(f"Training job {job_id} not found")
            return {"status": "error", "message": f"Training job {job_id} not found"}
        
        # Initialize replicate client
        client = ReplicateClient()
        
        # Prepare webhook events filter
        webhook_events_filter = ["start", "output", "logs", "completed"]
        
        # Start the training
        try:
            result = client.train_lora(
                training_images=training_image_urls,
                model_name=model_name,
                class_word=class_word,
                instance_prompt=instance_prompt,
                num_training_steps=num_training_steps,
                learning_rate=learning_rate,
                webhook_url=webhook_url,
                webhook_events_filter=webhook_events_filter
            )
            
            # Update job with prediction ID and initial status
            training_job.replicate_id = result.get("id")
            training_job.status = "processing"
            training_job.replicate_version = result.get("urls", {}).get("get")  # Store URL to prediction
            training_job.save()
            
            # If client webhook URL is provided, send notification
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "job_id": str(job_id),
                        "status": "processing",
                        "message": "LoRA training job started successfully"
                    }
                )
            
            return {
                "status": "success",
                "job_id": str(job_id),
                "replicate_id": result.get("id"),
                "message": "LoRA training job started successfully"
            }
            
        except Exception as e:
            logger.error(f"Error starting LoRA training: {str(e)}")
            
            # Update job with error status
            training_job.status = "failed"
            training_job.error_message = str(e)
            training_job.save()
            
            # If client webhook URL is provided, send error notification
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "job_id": str(job_id),
                        "status": "failed",
                        "message": f"Error starting LoRA training: {str(e)}"
                    }
                )
            
            # Retry if it's a connection error
            if "Connection" in str(e):
                raise self.retry(exc=e, countdown=10)
                
            return {
                "status": "error",
                "job_id": str(job_id),
                "message": f"Error starting LoRA training: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in start_lora_training task: {str(e)}")
        return {
            "status": "error",
            "job_id": str(job_id) if job_id else None,
            "message": f"Unexpected error: {str(e)}"
        }
        
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def handle_lora_training_webhook(self, job_id, payload, client_webhook_url=None):
    """Handle webhook notifications from Replicate for LoRA training jobs.
    
    Args:
        job_id: The ID of the LoraTrainingJob to update
        payload: The webhook payload from Replicate
        client_webhook_url: Optional webhook URL to notify client of updates
    
    Returns:
        Dictionary with processing status
    """
    try:
        # Add a small delay to ensure Redis connection is stable (for containerized environments)
        time.sleep(1)
        
        # Import here to avoid circular imports
        from model_training.models import LoraTrainingJob, TrainedModel
        
        # Get the training job
        try:
            training_job = LoraTrainingJob.objects.get(id=job_id)
        except LoraTrainingJob.DoesNotExist:
            logger.error(f"Training job {job_id} not found")
            return {"status": "error", "message": f"Training job {job_id} not found"}
        
        # Extract status from payload
        status = payload.get("status")
        
        # Update training job status
        training_job.status = status
        
        # Handle different statuses
        if status == "succeeded":
            # Extract output (URL to the trained model)
            output = payload.get("output")
            
            if isinstance(output, dict) and "lora_url" in output:
                model_url = output["lora_url"]
                training_job.model_url = model_url
                
                # Create a trained model entry
                trained_model = TrainedModel.objects.create(
                    name=training_job.model_name,
                    model_url=model_url,
                    class_word=training_job.class_word,
                    instance_prompt=training_job.instance_prompt,
                    training_job=training_job
                )
                
                logger.info(f"Created trained model {trained_model.id} for job {job_id}")
                
            else:
                logger.warning(f"No model URL found in output for job {job_id}")
                training_job.error_message = "No model URL in webhook payload"
                
        elif status == "failed":
            # Extract error message if available
            error = payload.get("error")
            if error:
                training_job.error_message = error
                logger.error(f"Training job {job_id} failed: {error}")
        
        # Save updates
        training_job.save()
        
        # If client webhook URL is provided, send notification
        if client_webhook_url:
            notification_data = {
                "job_id": str(job_id),
                "status": status,
                "message": f"LoRA training job status updated to {status}"
            }
            
            # Add model URL if available for succeeded jobs
            if status == "succeeded" and hasattr(training_job, "model_url") and training_job.model_url:
                notification_data["model_url"] = training_job.model_url
            
            # Add error message for failed jobs
            if status == "failed" and training_job.error_message:
                notification_data["error"] = training_job.error_message
                
            send_client_webhook(client_webhook_url, notification_data)
        
        return {
            "status": "success",
            "job_id": str(job_id),
            "message": f"Updated LoRA training job status to {status}"
        }
        
    except Exception as e:
        logger.error(f"Error handling LoRA training webhook: {str(e)}")
        
        # Retry if it's a database or connection error
        if "Connection" in str(e) or "database" in str(e).lower():
            raise self.retry(exc=e, countdown=5)
            
        return {
            "status": "error",
            "job_id": str(job_id),
            "message": f"Error handling webhook: {str(e)}"
        }
