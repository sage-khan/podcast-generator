import os
import uuid
import hmac
import hashlib
import logging
from urllib.parse import urljoin
from django.urls import reverse
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_webhook_secret():
    """
    Generate a unique webhook secret
    
    Returns:
        str: A random UUID string
    """
    return str(uuid.uuid4())


def generate_webhook_url(view_name, job_id, secret, request=None):
    """
    Generate a webhook URL for a job
    
    Args:
        view_name (str): Name of the view to call (include namespace)
        job_id (str): ID of the job
        secret (str): Webhook secret for security validation
        request (HttpRequest, optional): Request object to get host from
        
    Returns:
        str: Full webhook URL
    """
    # Ensure view_name includes the namespace
    if ':' not in view_name:
        # Instead of assuming 'api' namespace which doesn't exist,
        # use the correct app-specific namespace based on the view name
        if view_name in ['character_webhook', 'pose_webhook', 'lora_generation_webhook']:
            view_name = f'image_generation:{view_name}'
        elif view_name == 'lora_webhook':
            view_name = f'model_training:{view_name}'
    
    # Map the job_id to the correct parameter name based on the view
    kwargs = {'secret': secret}
    if 'character_webhook' in view_name:
        kwargs['character_id'] = job_id
    elif 'pose_webhook' in view_name:
        kwargs['pose_id'] = job_id
    elif 'lora_webhook' in view_name or 'lora-gen' in view_name or 'lora_generation_webhook' in view_name:
        kwargs['job_id'] = job_id
    else:
        # Default fallback
        kwargs['job_id'] = job_id
    
    # Generate the path without the domain
    webhook_path = reverse(view_name, kwargs=kwargs)
    
    # Get base URL from settings or environment
    base_url = getattr(settings, 'WEBHOOK_BASE_URL', None)
    if not base_url and request:
        # Try to get from request
        host = request.get_host()
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{host}"
    
    if not base_url:
        # Fallback to environment variable
        base_url = os.getenv('WEBHOOK_BASE_URL', 'https://example.com')
    
    # Always ensure we're using HTTPS (required by Replicate)
    if base_url.startswith('http://'):
        base_url = base_url.replace('http://', 'https://')
    elif not base_url.startswith('https://'):
        base_url = f"https://{base_url}"
    
    # Join the base URL with the path
    webhook_url = urljoin(base_url, webhook_path)
    
    logger.info(f"Generated webhook URL: {webhook_url}")
    return webhook_url


def validate_webhook_secret(secret, expected_secret):
    """
    Validate a webhook secret using constant-time comparison
    
    Args:
        secret (str): Secret from the webhook request
        expected_secret (str): Expected secret stored for the job
        
    Returns:
        bool: True if the secret is valid, False otherwise
    """
    if not secret or not expected_secret:
        logger.warning("Missing webhook secret or expected secret")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(secret, expected_secret)


def process_replicate_webhook(payload, model, client_webhook_url=None):
    """
    Process a webhook from Replicate
    
    Args:
        payload (dict): The webhook payload from Replicate
        model: The model instance to update (must have status field)
        client_webhook_url (str, optional): URL to send callback to client
        
    Returns:
        bool: True if processed successfully, False otherwise
    """
    try:
        logger.info(f"Processing Replicate webhook: {payload.get('status')}")
        
        # Extract the relevant data from the webhook payload
        status = payload.get('status')
        prediction_id = payload.get('id')
        output = payload.get('output')
        error = payload.get('error')
        urls = payload.get('urls', {})
        replicate_url = urls.get('get') if urls else None
        
        # Map Replicate status to our status
        status_mapping = {
            'starting': 'processing',
            'processing': 'processing',
            'succeeded': 'succeeded',
            'failed': 'failed',
            'canceled': 'failed'
        }
        
        internal_status = status_mapping.get(status, 'processing')
        
        # Update the model with the status and other information
        model.status = internal_status
        
        # Store the replicate URL if available
        if replicate_url and hasattr(model, 'replicate_url'):
            model.replicate_url = replicate_url
        
        # Handle successful job outputs
        if output and internal_status == 'succeeded':
            # Audio job handling (MinimaxSpeechJob, MinimaxVoiceCloneJob)
            if hasattr(model, 'output_url'):
                logger.info(f"Processing audio output for {model.__class__.__name__} {model.id}")
                
                # For audio jobs, output might be a string URL or a dict with 'audio' key
                if isinstance(output, dict) and output.get('audio'):
                    model.output_url = output['audio']
                elif isinstance(output, str):
                    model.output_url = output
                
                # Also set audio_url if that field exists
                if hasattr(model, 'audio_url') and model.output_url:
                    model.audio_url = model.output_url
                
                # For GoogleVeo3VideoJob, also set video_url to match output_url for frontend compatibility
                if model.__class__.__name__ == 'GoogleVeo3VideoJob' and hasattr(model, 'video_url') and model.output_url:
                    logger.info(f"Setting video_url to match output_url for Google Veo-3 job {model.id}")
                    model.video_url = model.output_url
                
                logger.info(f"Set audio output URL: {model.output_url}")
                
                # For video lipsync jobs, also handle video output
                if model.__class__.__name__ == 'KlingLipsyncJob':
                    # If it's a dict with 'video' key or 'url' key
                    video_url = None
                    if isinstance(output, dict):
                        video_url = output.get('video') or output.get('url')
                    
                    # If output is a direct URL
                    if not video_url and isinstance(output, str):
                        video_url = output
                    
                    # Store the video URL
                    if video_url:
                        logger.info(f"Setting video output URL to {video_url}")
                        model.video_output_url = video_url
            
            # Image job handling (with output_urls field)
            elif hasattr(model, 'output_urls'):
                output_urls = []
                if isinstance(output, list):
                    output_urls = output
                elif isinstance(output, str):
                    output_urls = [output]
                
                model.output_urls = output_urls
                
                # Download and save images both locally and to Digital Ocean Spaces
                if output_urls:
                    try:
                        import requests
                        import os
                        from django.conf import settings
                        from pathlib import Path
                        import uuid
                        
                        # Determine model type for folder structure
                        if hasattr(model, '__class__') and model.__class__.__name__ == 'Character':
                            folder_name = 'characters'
                        elif hasattr(model, '__class__') and model.__class__.__name__ == 'Pose':
                            folder_name = 'poses'
                        else:
                            folder_name = 'images'
                        
                        # Ensure local media directory exists
                        local_media_dir = Path(settings.MEDIA_ROOT) / folder_name
                        os.makedirs(local_media_dir, exist_ok=True)
                        
                        # Get Digital Ocean storage client
                        from shared.clients.storage_client import storage_client
                        
                        saved_urls = []
                        for i, img_url in enumerate(output_urls):
                            # Generate a unique filename
                            file_ext = os.path.splitext(img_url)[1] or '.jpg'
                            if not file_ext.startswith('.'):
                                file_ext = f'.{file_ext}'
                            
                            filename = f"{model.id}_{i}{file_ext}"
                            
                            # Download the image
                            response = requests.get(img_url, stream=True)
                            if response.status_code == 200:
                                # Save locally
                                local_path = local_media_dir / filename
                                with open(local_path, 'wb') as f:
                                    for chunk in response.iter_content(1024):
                                        f.write(chunk)
                                
                                # Save to Digital Ocean Spaces
                                if storage_client:
                                    do_path = f"{folder_name}/{filename}"
                                    with open(local_path, 'rb') as f:
                                        storage_client.upload_file(f, do_path)
                                    
                                    # Get the public URL
                                    do_url = storage_client.get_public_url(do_path)
                                    saved_urls.append(do_url)
                                    
                                    # Set the main image URL to the first one
                                    if i == 0 and hasattr(model, 'image_url'):
                                        model.image_url = do_url
                                else:
                                    # Use local URL if DO storage not available
                                    local_url = f"/media/{folder_name}/{filename}"
                                    saved_urls.append(local_url)
                                    
                                    # Set the main image URL to the first one
                                    if i == 0 and hasattr(model, 'image_url'):
                                        model.image_url = local_url
                        
                        logger.info(f"Saved {len(saved_urls)} images for {model.__class__.__name__} {model.id}")
                        
                    except Exception as download_error:
                        logger.error(f"Error downloading images: {str(download_error)}")
                        # Continue with the original URLs if download fails
                        if hasattr(model, 'image_url') and output_urls and not model.image_url:
                            model.image_url = output_urls[0]
        
        # Extract voice_id for voice-clone jobs
        if internal_status == 'succeeded' and hasattr(model, 'voice_id'):
            extracted_voice_id = None
            preview_url = None
            # Replicate can return either a dict or a simple string
            if isinstance(output, dict):
                extracted_voice_id = output.get('voice_id')
                preview_url = output.get('preview_url') or output.get('preview')
            elif isinstance(output, str):
                extracted_voice_id = output

            if extracted_voice_id:
                model.voice_id = extracted_voice_id
            if preview_url and hasattr(model, 'preview'):
                model.preview = preview_url
        
        # Store any error message
        if error and hasattr(model, 'error_message'):
            model.error_message = error
        
        # Save the model
        model.save()
        logger.debug(f"Saved job {model.id} with status {model.status}")
        logger.debug(f"Model saved to database: {model.__dict__}")
        
        # Call the client webhook if provided
        if client_webhook_url and internal_status in ['succeeded', 'failed']:
            send_client_webhook(client_webhook_url, model)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing Replicate webhook: {str(e)}")
        return False


def send_client_webhook(client_webhook_url, model_or_payload):
    """
    Send a webhook to the client.
    
    This helper now accepts *either* a Django model instance **or** a plain
    ``dict`` that is already suitable for JSON serialisation.  Passing a
    dict allows callers to customise the payload without needing a model
    object and avoids attribute-access errors (e.g. ``'dict' object has no
    attribute 'status'``) that we previously saw in the logs.
    
    Args:
        client_webhook_url (str): URL to send the webhook to
        model_or_payload (Model | dict): Either the job / task model *or* a
            ready-made payload dict.
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    import requests
    
    try:
        logger.info(f"Sending client webhook to: {client_webhook_url}")
        
        # ------------------------------------------------------------------
        # Build the payload
        # ------------------------------------------------------------------
        if isinstance(model_or_payload, dict):
            # Caller supplied a ready-made payload → use as-is.  Do *not* mutate
            # the original dict to avoid side-effects.
            payload = model_or_payload.copy()
        else:
            model = model_or_payload
            payload = {
                'status': getattr(model, 'status', None),
                'job_id': str(getattr(model, 'id', '')),
            }
            
            # Add optional fields if present on the model
            if getattr(model, 'output_urls', None):
                payload['output_urls'] = model.output_urls
            if getattr(model, 'output_url', None):
                payload['output_url'] = model.output_url
            if getattr(model, 'video_url', None):  # KlingLipsyncJob, etc.
                payload['video_url'] = model.video_url
            if getattr(model, 'error_message', None):
                payload['error'] = model.error_message
            if getattr(model, 'replicate_url', None):
                payload['replicate_url'] = model.replicate_url
            if getattr(model, 'replicate_model_version', None):
                payload['model_version'] = model.replicate_model_version
            if getattr(model, 'voice_id', None):
                payload['voice_id'] = model.voice_id
        
        # ------------------------------------------------------------------
        # Fire the webhook
        # ------------------------------------------------------------------
        response = requests.post(
            client_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10,
        )
        
        response.raise_for_status()
        logger.info(f"Client webhook sent successfully: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending client webhook: {str(e)}")
        return False


def generate_client_webhook_notification(client_webhook_url, data):
    """
    Send a webhook notification to the client with custom data
    
    Args:
        client_webhook_url (str): URL to send the webhook to
        data (dict): Custom data to send in the webhook
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    import requests
    
    try:
        logger.info(f"Sending client notification to: {client_webhook_url}")
        
        # Send the webhook with the provided data
        response = requests.post(
            client_webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        response.raise_for_status()
        logger.info(f"Client notification sent successfully: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending client notification: {str(e)}")
        return False