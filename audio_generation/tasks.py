import logging
import traceback
import uuid

import replicate
from django.utils import timezone
from django.db import transaction
from celery import shared_task
from urllib.parse import urlparse

from audio_generation.models import MinimaxVoiceCloneJob, MinimaxSpeechJob
from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import storage_client
from shared.utils.webhook_utils import send_client_webhook
import os

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2)
def generate_minimax_voice_clone(self, job_id, webhook_url=None):
    """
    Generate audio using the Minimax voice clone model
    
    Args:
        job_id (str): UUID of the MinimaxVoiceCloneJob
        webhook_url (str, optional): Webhook URL to receive updates
    """
    logger.info(f"Starting Minimax voice clone generation for job {job_id}")
    
    try:
        # Get the voice clone job
        job = MinimaxVoiceCloneJob.objects.get(id=job_id)
        
        # Update status to processing
        job.status = 'processing'
        job.save(update_fields=['status'])
        
        if job.client_webhook_url:
            # Send initial webhook to client
            send_client_webhook(job.client_webhook_url, {
                'id': str(job.id),
                'status': job.status,
            })
        
        # Generate an accessible URL (presigned if needed) for the voice file
        try:
            accessible_voice_file = storage_client.get_accessible_url(job.voice_file, expires_in=3600)
            logger.info(f"Generated accessible URL for voice file: {accessible_voice_file}")
        except Exception as e:
            logger.error(f"Error generating accessible URL for voice file: {str(e)}")
            raise
        
        # Create the input dictionary for Replicate
        input_dict = {
            'voice_file': accessible_voice_file,  # Use the accessible URL instead of the original
            'model': job.model,
            'accuracy': job.accuracy,
            'need_noise_reduction': job.need_noise_reduction,
            'need_volume_normalization': job.need_volume_normalization
        }
        
        # Initialize Replicate client
        replicate_client = ReplicateClient()
        
        # Get the model version (using the minimax/voice-cloning model)
        voice_clone_model = "minimax/voice-cloning"
        
        # Run the prediction with webhook URL if provided
        webhook_params = {}
        if webhook_url:
            webhook_params = {
                'webhook': webhook_url,
                'webhook_events_filter': ["completed", "start", "output", "logs"]
            }
        
        logger.info(f"Running Replicate prediction for job {job_id} with webhook URL: {webhook_url}")

        # Use direct API calls instead of the Python client
        import requests

        # Get API token 
        api_token = os.environ.get("REPLICATE_API_TOKEN")

        # Prepare API request
        headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }

        # Prepare payload - version is required, model is not allowed in payload
        payload = {
            "version": voice_clone_model,  # Use the model name as version
            "input": input_dict,
        }

        # Add webhook if provided
        if webhook_url:
            payload["webhook"] = webhook_url
            payload["webhook_events_filter"] = ["completed", "start", "output", "logs"]

        # Make direct API call
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            json=payload,
            headers=headers
        )

        
        if response.status_code >= 400:
            raise Exception(f"Replicate API error: {response.text}")
            
        response_data = response.json()

        # Create a mock prediction object with the same interface
        class MockPrediction:
            def __init__(self, data):
                self.id = data.get("id")
                self.url = data.get("urls", {}).get("get")
                self._data = data
                    
            def wait(self):
                # This method is used in the synchronous path
                # We'd need to poll for completion, but this won't be called
                # when webhooks are used
                return None
            
        prediction = MockPrediction(response_data)
        
        # Store the Replicate URL and ID
        job.replicate_url = prediction.url
        job.replicate_id = response_data.get("id")  # Store the Replicate prediction ID
        
        # Log more details about the response for debugging
        logger.info(f"Replicate response data: {response_data}")
        
        # Save both fields
        job.save(update_fields=['replicate_url', 'replicate_id'])
        
        logger.info(f"Replicate prediction started for job {job_id}, URL: {prediction.url}, ID: {job.replicate_id}")
        
        # If no webhook is provided, wait for the prediction to complete
        if not webhook_url:
            # Wait for the prediction to complete
            result = prediction.wait()   # might be url or dict
            if isinstance(result, dict):
                job.voice_id = result.get('voice_id')
                job.preview = result.get('preview_url')
                job.output_url = result.get('preview_url')  # fallback for output_url
            else:
                job.output_url = result
            
            # Update status
            job.status = 'succeeded'
            job.completed_at = timezone.now()
            job.save(update_fields=['output_url', 'status', 'completed_at', 'voice_id', 'preview'])
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'output_url': job.output_url,
                })
                
            logger.info(f"Minimax voice clone generation completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in generate_minimax_voice_clone: {str(e)}\n{traceback.format_exc()}")
        
        try:
            # Update job status to failed
            job = MinimaxVoiceCloneJob.objects.get(id=job_id)
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
def generate_minimax_speech(self, job_id, webhook_url=None):
    """
    Generate audio using the Minimax speech models (HD or Turbo)
    
    Args:
        job_id (str): UUID of the MinimaxSpeechJob
        webhook_url (str, optional): Webhook URL to receive updates
    """
    logger.info(f"Starting Minimax speech generation for job {job_id}")
    job = None
    
    try:
        # Get the speech job
        job = MinimaxSpeechJob.objects.get(id=job_id)
        
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
            'text': job.text,
            'voice_id': job.voice_id,
            'language': job.language,
            'speed': job.speed,
            'pitch': job.pitch,
            'volume': job.volume,
            'bitrate': job.bitrate,
            'channel': job.channel,
            'emotion': job.emotion,
            'sample_rate': job.sample_rate,
            **({"language_boost": job.language_boost} if job.language_boost not in [None, "", "None"] else {}),
            'english_normalization': job.english_normalization,
        }
        
        # Log input parameters for debugging
        logger.info(f"Input parameters for job {job_id}: {input_dict}")
        
        # Initialize Replicate client
        replicate_client = ReplicateClient()
        
        # Determine which model to use based on model_version   
         
        if job.model_version == 'hd':
            model_speech_gen = "minimax/speech-02-hd"
        else:  # turbo
            model_speech_gen = "minimax/speech-02-turbo"
        
        # Run the prediction with webhook URL if provided
        webhook_params = {}
        if webhook_url:
            webhook_params = {
                'webhook': webhook_url,
                'webhook_events_filter': ["completed", "start", "output", "logs"]
            }
        
        logger.info(f"Running Replicate prediction for job {job_id} with webhook URL: {webhook_url}")
        
        prediction = replicate.predictions.create(
                version=model_speech_gen,
                input=input_dict,
                **webhook_params
            )
        job.replicate_url = prediction.urls.get("get")  # Use the API endpoint URL
        job.save(update_fields=['replicate_url'])

        logger.info(f"Replicate prediction started for job {job_id}, URL: {job.replicate_url}, ID: {prediction.id}")
        
        # ------------------------------------------------------------------
        # Decide whether to wait synchronously for the Replicate prediction.
        # ------------------------------------------------------------------
        env_force_wait   = os.getenv("REPLICATE_FORCE_WAIT", "false").lower() == "true"
        webhook_unusable = webhook_url is None or "localhost" in webhook_url or "127." in webhook_url

        should_wait = env_force_wait or webhook_unusable

        if should_wait:
            logger.info(
                f"Waiting for Replicate prediction to complete for job {job_id}. "
                f"env_force_wait={env_force_wait}, webhook_unusable={webhook_unusable}"
            )

            # Wait for the prediction to complete (can take a while)
            result = prediction.wait()   # might be URL or dict
            
            logger.info(f"Prediction completed for job {job_id}, result type: {type(result)}")
            
            if isinstance(result, dict):
                job.output_url = result.get('audio') or result.get('output')
                logger.info(f"Result is dict, output_url: {job.output_url}")
            else:
                job.output_url = result
                logger.info(f"Result is string: {job.output_url}")
            
            # Update status
            job.status = 'succeeded'
            job.completed_at = timezone.now()
            job.save()
            
            logger.info(f"Job {job_id} completed successfully (synchronous wait), output_url: {job.output_url}")
            
            # Send webhook to client if configured
            if job.client_webhook_url:
                send_client_webhook(job.client_webhook_url, {
                    'id': str(job.id),
                    'status': job.status,
                    'output_url': job.output_url,
                })
                
            logger.info(f"Minimax speech generation completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in generate_minimax_speech: {str(e)}\n{traceback.format_exc()}")
        
        try:
            # Update job status to failed
            job = MinimaxSpeechJob.objects.get(id=job_id)
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
