import logging
import os
import time
import json
import requests
import replicate
import tempfile
import uuid
import boto3
import django.db.utils
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlparse

from shared.utils.task_utils import with_task_logging
from config.celery import app
from .models import LoraTrainingJob
from image_generation.models import Character, Pose
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_or_create_model(model_name, owner=None):
    """Get an existing model or create it if it doesn't exist"""
    # Set default owner
    if owner is None:
        owner = os.getenv('REPLICATE_OWNER', 'your-replicate-username')
    
    # Validate model name - remove any invalid characters that might cause API issues
    import re
    safe_model_name = re.sub(r'[^a-zA-Z0-9_\-]', '-', model_name)
    safe_model_name = safe_model_name[:50]  # Limit length to avoid API issues
    
    model_key = f"{owner}/{safe_model_name}"
    logger.info(f"🔍 Checking if model exists: {model_key}")
    
    try:
        # Attempt to retrieve the existing model
        model = replicate.models.get(model_key)
        logger.info(f"✅ Using existing model: {model_key}")
        return model
    except replicate.exceptions.ReplicateError as e:
        if "404" in str(e):
            logger.info(f"❌ Model '{safe_model_name}' not found. Creating a new one...")
        else:
            logger.error(f"❌ Unexpected error: {e}")
            raise e
    
    # If we're here, the model wasn't found (404 error) - create a new one
    try:
        # Create a new model
        model = replicate.models.create(
            name=safe_model_name,
            owner=owner,
            visibility="public",
            description=f"Fine-tuned FLUX.1 model for {safe_model_name}",
            hardware="gpu-a100-large"
        )
        logger.info(f"✅ New model created: {owner}/{model.name}")
        logger.info(f"🔗 Model URL: https://replicate.com/{owner}/{model.name}")
        return model
    except Exception as create_error:
        logger.error(f"❌ Failed to create model with name '{safe_model_name}': {str(create_error)}")
        
        # Try with fallback timestamp name if the original name fails
        try:
            fallback_name = f"lora-{int(time.time())}"
            logger.info(f"🔄 Attempting with fallback name: {fallback_name}")
            
            model = replicate.models.create(
                name=fallback_name,
                owner=owner,
                visibility="public",
                description=f"Fine-tuned FLUX.1 model (fallback creation)",
                hardware="gpu-a100-large"
            )
            logger.info(f"✅ Model created with fallback name: {owner}/{model.name}")
            logger.info(f"🔗 Model URL: https://replicate.com/{owner}/{model.name}")
            return model
        except Exception as fallback_error:
            logger.error(f"❌ Fallback creation also failed: {str(fallback_error)}", exc_info=True)
            if "permission" in str(fallback_error).lower() or "unauthorized" in str(fallback_error).lower():
                logger.error(f"🔐 This appears to be a permissions issue. Please check that the API token has write access to the {owner} account.")
            raise fallback_error

def download_training_data(url, output_path=None):
    """
    Download training data from URL to a local file
    
    Args:
        url: URL to download from (e.g., https://spacename.region.cdn.digitaloceanspaces.com/path/to/file.zip)
        output_path: Path to save the file to (optional, will create a temp file if not provided)
        
    Returns:
        Path to the downloaded file or None if download failed
    """
    if not output_path:
        # Create a temporary file with .zip extension
        temp_dir = tempfile.gettempdir()
        unique_id = uuid.uuid4().hex
        output_path = os.path.join(temp_dir, f"training_data_{unique_id}.zip")
    
    logger.info(f"⏳ Downloading training data from: {url} to {output_path}")
    try:
        # Parse the URL to get the bucket and key parts
        parsed_url = urlparse(url)
        
        # Extract bucket name and region from the hostname
        # Example: aicc.nyc3.cdn.digitaloceanspaces.com
        hostname_parts = parsed_url.netloc.split('.')
        if len(hostname_parts) < 4 or not hostname_parts[2] == "cdn": # basic validation for DO CDN structure
            logger.error(f"❌ Invalid DigitalOcean Spaces CDN URL format: {parsed_url.netloc}. Expected format like 'spacename.region.cdn.digitaloceanspaces.com'.")
            return None
            
        bucket_name = hostname_parts[0]
        region_name = hostname_parts[1]
        
        # Construct the S3 endpoint URL for DigitalOcean Spaces
        s3_endpoint_url = f"https://{region_name}.digitaloceanspaces.com"
        
        # Ensure DO_SPACES_KEY and DO_SPACES_SECRET are set as 
        # AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the environment.
        s3 = boto3.client(
            's3',
            endpoint_url=s3_endpoint_url,
            region_name=region_name 
            # Credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) are picked up from env
        )
        
        object_key = parsed_url.path
        if object_key.startswith('/'):
            object_key = object_key[1:]  # Remove leading slash for the S3 object key
            
        logger.info(f"Downloading from Bucket: {bucket_name}, Key: {object_key}, Endpoint: {s3_endpoint_url}")
        
        # Use storage client to download the file with authentication
        with open(output_path, 'wb') as f:
            s3.download_fileobj(
                Bucket=bucket_name, 
                Key=object_key, 
                Fileobj=f
            )
        
        # Verify file was downloaded successfully
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✅ Download complete: {output_path} ({os.path.getsize(output_path)} bytes)")
            return output_path
        else:
            logger.error(f"❌ Downloaded file is empty or does not exist: {output_path}")
            # Clean up the empty file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as e_rm:
                    logger.warning(f"Could not remove empty/failed download {output_path}: {e_rm}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error downloading file: {str(e)}", exc_info=True)
        # Clean up the partial file if it exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError as e_rm_ex:
                logger.warning(f"Could not remove partial download {output_path} on exception: {e_rm_ex}")
        return None

@app.task(
    bind=True,
    max_retries=5, 
    retry_backoff=True,
    rate_limit="5/m",
    name="model_training.tasks.start_lora_training"
)
@with_task_logging
def start_lora_training(self, job_id, *args, **kwargs):
    """
    Start a LoRA training job with Replicate
    
    Args:
        job_id: ID of the LoraTrainingJob
        *args, **kwargs: Additional arguments (ignored, for compatibility with other implementations)
    """
    logger.info(f"Starting LoRA training job {job_id}")
    downloaded_files = []  # Track downloaded files for cleanup
    
    try:
        # Get the job from database
        training_job = LoraTrainingJob.objects.get(id=job_id)
        
        # Mark as processing
        training_job.status = "processing"
        training_job.started_at = timezone.now()
        training_job.save(update_fields=["status", "started_at"])
        
        # Generate or get webhook URL with secret
        base_url = settings.WEBHOOK_BASE_URL
        if not base_url.startswith('https://'):
            logger.warning(f"Webhook base URL {base_url} doesn't use HTTPS, which is required by Replicate")
            base_url = base_url.replace('http://', 'https://')
            
        # Create webhook URL with namespace
        webhook_path = reverse('model_training:lora_webhook', kwargs={'job_id': training_job.id, 'secret': training_job.webhook_secret})
        webhook_url = f"{base_url}{webhook_path}"
        
        # Parse model ID into owner/name and version parts
        model_parts = settings.REPLICATE_LORA_TRAINER_MODEL.split(":")
        if len(model_parts) != 2:
            raise ValueError(f"Invalid model ID format: {settings.REPLICATE_LORA_TRAINER_MODEL}")
        
        model = model_parts[0]  # owner/name
        version = model_parts[1]  # version hash
        
        # Prepare training inputs according to OSTRIS LoRA dev trainer documentation
        training_inputs = {
            # Required parameters
            "trigger_word": training_job.trigger_word,
            # We'll replace input_images with file data after downloading
            "steps": training_job.steps,
            
            # Standard parameters with model defaults
            "lora_rank": training_job.lora_rank,
            "resolution": f"{training_job.resolution},{training_job.resolution},{training_job.resolution}",
            "batch_size": training_job.batch_size,
            "learning_rate": training_job.learning_rate,
            
            # Additional parameters with default values from documentation
            "optimizer": "adamw8bit",
            "autocaption": True,
            "caption_dropout_rate": 0.05,
            # cache_latents_to_disk has been removed from the API
            "gradient_checkpointing": False,
            "wandb_project": "flux_train_replicate",
            
            # Webhook configuration for status updates
            "webhook": webhook_url,
            "webhook_events_filter": ["start", "output", "logs", "completed"]
        }
        
        # First try to get or create the model
        try:
            # Use simplified model name to avoid API issues
            import re
            simplified_model_name = re.sub(r'[^a-zA-Z0-9_\-]', '-', training_job.model_name)
            simplified_model_name = simplified_model_name[:50]  # Limit length
            
            logger.info(f"🔄 Using simplified model name: {simplified_model_name}")
            destination_model = get_or_create_model(
                simplified_model_name,
                training_job.replicate_model_owner or None
            )
        except Exception as model_error:
            # Direct fallback approach in case the get_or_create_model function fails entirely
            logger.error(f"❌ get_or_create_model failed: {str(model_error)}")
            logger.info(f"🔄 Using direct model creation as fallback")
            
            # Get model owner or use default
            owner = training_job.replicate_model_owner or os.getenv('REPLICATE_OWNER', 'your-replicate-username')
            
            # Always use a timestamp for maximum reliability
            fallback_name = f"lora-{int(time.time())}"
            destination_model = replicate.models.create(
                name=fallback_name,
                owner=owner,
                visibility="public",
                description=f"Fine-tuned FLUX.1 model (emergency fallback creation)",
                hardware="gpu-a100-large"
            )
            logger.info(f"✅ Emergency fallback model created: {owner}/{destination_model.name}")
        
        # Download training data from URL
        # input_image_urls might be a string or a list - handle both cases
        input_urls = training_job.input_image_urls
        if isinstance(input_urls, str):
            input_urls = [input_urls]
        
        logger.info(f"Downloading {len(input_urls)} training data file(s)")
        
        # Start the training
        logger.info(f"Starting Replicate training with webhook: {webhook_url}")
        
        # Only download and process one file at a time - we'll open each before passing to Replicate
        # We only support one training data file for now
        if len(input_urls) > 0:
            # Download the training data
            training_data_path = download_training_data(input_urls[0])
            if not training_data_path or not os.path.exists(training_data_path):
                raise Exception(f"Failed to download training data from URL: {input_urls[0]}")
            
            downloaded_files.append(training_data_path)
            
            # Open the training data file for passing to Replicate
            with open(training_data_path, "rb") as training_data_file:
                # Log the final training inputs without the file contents
                log_inputs = training_inputs.copy()
                log_inputs["input_images"] = f"[File data from {input_urls[0]}]"
                logger.info(f"Training inputs: {json.dumps(log_inputs, indent=2)}")
                
                # Use trainings.create with the model - important to use destination_model.name
                training = replicate.trainings.create(
                    # Define the destination model using the returned model's name
                    destination=f"{training_job.replicate_model_owner or 'your-replicate-username'}/{destination_model.name}",
                    # Specify the trainer model version
                    version=f"{model}:{version}",
                    input={
                        **training_inputs,
                        "input_images": training_data_file  # Pass the file object instead of URL
                    }
                )
        else:
            logger.error("No training data URLs provided")
            raise ValueError("No training data URLs provided")
        
        # Update job with training info
        training_job.replicate_training_id = training.id
        training_job.status = 'processing'
        training_job.save()
        
        logger.info(f"Started training job with ID: {training.id}")
        
        # If client webhook URL is provided, notify of job start
        if training_job.client_webhook_url:
            try:
                requests.post(
                    training_job.client_webhook_url,
                    json={
                        "status": "processing",
                        "job_id": str(training_job.id),
                        "message": "LoRA training job started",
                        "replicate_id": training.id,
                        "timestamp": timezone.now().isoformat()
                    },
                    timeout=5
                )
                logger.info(f"Notified client webhook of job start: {training_job.client_webhook_url}")
            except Exception as e:
                logger.error(f"Failed to notify client webhook: {str(e)}")
        
        return {
            "job_id": str(training_job.id),
            "status": "processing",
            "replicate_id": training.id
        }
        
    except LoraTrainingJob.DoesNotExist:
        logger.error(f"LoRA training job {job_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error starting LoRA training job {job_id}: {str(e)}", exc_info=True)
        
        # Update job status if it exists
        try:
            training_job = LoraTrainingJob.objects.get(id=job_id)
            training_job.status = "failed"
            training_job.error_message = str(e)
            training_job.save(update_fields=["status", "error_message"])
            
            # Notify client webhook of failure if provided
            if training_job.client_webhook_url:
                try:
                    requests.post(
                        training_job.client_webhook_url,
                        json={
                            "status": "failed",
                            "job_id": str(training_job.id),
                            "message": f"LoRA training job failed: {str(e)}",
                            "replicate_id": job_id,
                            "timestamp": timezone.now().isoformat()
                        },
                        timeout=5
                    )
                except Exception as webhook_err:
                    logger.error(f"Failed to notify client webhook of failure: {str(webhook_err)}")
                    
        except LoraTrainingJob.DoesNotExist:
            # Job was deleted during execution
            pass
            
        # Retry with backoff if appropriate
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries  # Exponential backoff
            raise self.retry(exc=e, countdown=retry_delay)
        raise
    finally:
        # Clean up downloaded files
        for file_path in downloaded_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")

@app.task(
    bind=True,
    name="model_training.tasks.check_pending_lora_jobs"
)
@with_task_logging
def check_pending_lora_jobs(self):
    """
    Check the status of all pending LoRA training jobs that might not have received a webhook callback
    This is a fallback mechanism in case Replicate's webhooks don't work properly
    """
    logger.info("Checking for pending LoRA training jobs")
    
    try:
        # Get jobs that have been processing for too long (e.g., 30 minutes)
        time_threshold = timezone.now() - timezone.timedelta(minutes=30)
        stalled_jobs = LoraTrainingJob.objects.filter(
            status="processing", 
            started_at__lt=time_threshold
        )
        
        logger.info(f"Found {stalled_jobs.count()} potentially stalled LoRA jobs")
        
        for job in stalled_jobs:
            try:
                # Skip jobs without a Replicate ID
                if not job.replicate_training_id:
                    logger.warning(f"Job {job.id} has no Replicate ID to check")
                    continue
                    
                # Check status with Replicate API
                replicate_status = replicate.trainings.get(job.replicate_training_id)
                
                # If status hasn't changed, continue to next job
                if replicate_status.status == job.status:
                    continue
                    
                logger.info(f"Job {job.id} status in Replicate is {replicate_status.status} but in DB is {job.status}")
                
                # Update job with current status from Replicate
                if replicate_status.status == "succeeded":
                    # Handle success - similar to webhook handler
                    job.status = "succeeded"
                    job.completed_at = timezone.now()
                    if hasattr(replicate_status, 'output') and replicate_status.output:
                        job.replicate_model_version = replicate_status.output.get("version", "")
                    job.save()
                    
                    logger.info(f"Updated job {job.id} to succeeded status")
                    
                    # Notify client webhook if available
                    if job.client_webhook_url:
                        try:
                            requests.post(
                                job.client_webhook_url,
                                json={
                                    "status": "succeeded",
                                    "job_id": str(job.id),
                                    "message": "LoRA training job completed successfully",
                                    "replicate_id": job.replicate_training_id,
                                    "model_version": job.replicate_model_version,
                                    "timestamp": timezone.now().isoformat()
                                },
                                timeout=5
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify client webhook of success: {str(e)}")
                    
                elif replicate_status.status in ["failed", "canceled"]:
                    # Handle failure - similar to webhook handler
                    job.status = replicate_status.status
                    job.error_message = getattr(replicate_status, 'error', 'Unknown error')
                    job.completed_at = timezone.now()
                    job.save()
                    
                    logger.info(f"Updated job {job.id} to {replicate_status.status} status")
                    
                    # Notify client webhook if available
                    if job.client_webhook_url:
                        try:
                            requests.post(
                                job.client_webhook_url,
                                json={
                                    "status": replicate_status.status,
                                    "job_id": str(job.id),
                                    "message": f"LoRA training job {replicate_status.status}: {job.error_message}",
                                    "replicate_id": job.replicate_training_id,
                                    "timestamp": timezone.now().isoformat()
                                },
                                timeout=5
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify client webhook of failure: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error checking status for job {job.id}: {str(e)}", exc_info=True)
        
        return f"Checked {stalled_jobs.count()} pending jobs"
    
    except django.db.utils.OperationalError as db_error:
        # Handle database connection errors (like missing certificates)
        if "sslrootcert" in str(db_error) or "certificate file" in str(db_error):
            logger.error(f"Database SSL certificate error: {str(db_error)}")
            logger.warning("Consider updating your database connection settings or ensuring the certificate is mounted correctly")
            return "Failed to check jobs due to database SSL certificate issue - fix by mounting certificate or updating settings"
        else:
            # Re-raise other operational errors
            logger.error(f"Database connection error: {str(db_error)}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error in check_pending_lora_jobs: {str(e)}", exc_info=True)
        raise