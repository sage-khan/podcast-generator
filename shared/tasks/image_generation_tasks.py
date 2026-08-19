import logging
import os
import time
from celery import shared_task

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import StorageClient
from shared.utils.webhook_utils import send_client_webhook
from shared.utils.webhook_utils import generate_client_webhook_notification

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_character_task(self, 
                          character_id, 
                          prompt, 
                          negative_prompt="", 
                          num_inference_steps=30, 
                          seed=None, 
                          webhook_url=None, 
                          client_webhook_url=None):
    """Generate a character image using Replicate in a background task.
    
    Args:
        character_id: UUID of the Character model instance
        prompt: Text description of the character to generate
        negative_prompt: Text description of what to avoid
        num_inference_steps: Number of inference steps
        seed: Optional random seed for generation
        webhook_url: Webhook URL for Replicate to send updates to
        client_webhook_url: Optional webhook URL to notify client of updates
        
    Returns:
        Dictionary with job status and details
    """
    try:
        # Add a small delay to ensure Redis connection is stable
        time.sleep(2)
        
        # Import here to avoid circular imports
        from image_generation.models import Character
        
        # Get character from database
        try:
            character = Character.objects.get(id=character_id)
            character.status = "processing"
            character.save()
        except Character.DoesNotExist:
            logger.error(f"Character {character_id} not found")
            return {"status": "error", "message": f"Character {character_id} not found"}
        
        # Initialize the Replicate client
        client = ReplicateClient()
        
        # Prepare webhook events filter
        webhook_events_filter = ["start", "output", "completed"]
        
        # Start generation
        try:
            result = client.generate_character(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                seed=seed,
                webhook_url=webhook_url,
                webhook_events_filter=webhook_events_filter
            )
            
            # Update character with prediction ID
            character.replicate_id = result.get("id")
            character.status = "processing"
            character.replicate_version = result.get("urls", {}).get("get")
            character.save()
            
            # Notify client if webhook URL is provided
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "character_id": str(character_id),
                        "status": "processing",
                        "message": "Character generation started"
                    }
                )
            
            return {
                "status": "success",
                "character_id": str(character_id),
                "replicate_id": result.get("id"),
                "message": "Character generation started"
            }
            
        except Exception as e:
            logger.error(f"Error generating character: {str(e)}")
            
            # Update character with error status
            character.status = "failed"
            character.error_message = str(e)
            character.save()
            
            # Notify client of error if webhook URL is provided
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "character_id": str(character_id),
                        "status": "failed",
                        "message": f"Error generating character: {str(e)}"
                    }
                )
            
            # Retry if it's a connection error
            if "Connection" in str(e):
                raise self.retry(exc=e, countdown=10)
                
            return {
                "status": "error",
                "character_id": str(character_id),
                "message": f"Error generating character: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in generate_character_task: {str(e)}")
        return {
            "status": "error",
            "character_id": str(character_id) if character_id else None,
            "message": f"Unexpected error: {str(e)}"
        }

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def handle_character_webhook(self, character_id, payload, client_webhook_url=None):
    """Handle webhook notifications from Replicate for character generation.
    
    Args:
        character_id: UUID of the Character to update
        payload: Webhook payload from Replicate
        client_webhook_url: Optional webhook URL to notify client of updates
        
    Returns:
        Dictionary with processing status
    """
    try:
        # Add a small delay to ensure Redis connection is stable
        time.sleep(1)
        
        # Import here to avoid circular imports
        from image_generation.models import Character
        
        # Get character from database
        try:
            character = Character.objects.get(id=character_id)
        except Character.DoesNotExist:
            logger.error(f"Character {character_id} not found")
            return {"status": "error", "message": f"Character {character_id} not found"}
        
        # Extract status from payload
        status = payload.get("status")
        
        # Update character status
        character.status = status
        
        # If succeeded, extract and save image URL
        if status == "succeeded":
            output = payload.get("output")
            if output and isinstance(output, list) and len(output) > 0:
                # Extract image URL from output
                image_url = output[0]
                character.image_url = image_url
                logger.info(f"Character {character_id} generated successfully: {image_url}")
                
                # Save image to storage if needed
                # This could be implemented here or in a separate task
                
            else:
                logger.warning(f"No image URL in output for character {character_id}")
                character.error_message = "No image URL in webhook payload"
                
        elif status == "failed":
            # Extract error message if available
            error = payload.get("error")
            if error:
                character.error_message = error
                logger.error(f"Character generation {character_id} failed: {error}")
        
        # Save updates
        character.save()
        
        # If client webhook URL is provided, send notification
        if client_webhook_url:
            notification_data = {
                "character_id": str(character_id),
                "status": status,
                "message": f"Character generation status updated to {status}"
            }
            
            # Add image URL if available for succeeded jobs
            if status == "succeeded" and character.image_url:
                notification_data["image_url"] = character.image_url
            
            # Add error message for failed jobs
            if status == "failed" and character.error_message:
                notification_data["error"] = character.error_message
                
            send_client_webhook(client_webhook_url, notification_data)
        
        return {
            "status": "success",
            "character_id": str(character_id),
            "message": f"Updated character generation status to {status}"
        }
        
    except Exception as e:
        logger.error(f"Error handling character webhook: {str(e)}")
        
        # Retry if it's a database or connection error
        if "Connection" in str(e) or "database" in str(e).lower():
            raise self.retry(exc=e, countdown=5)
            
        return {
            "status": "error",
            "character_id": str(character_id),
            "message": f"Error handling webhook: {str(e)}"
        }

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def generate_poses_task(self, 
                       pose_id, 
                       character_image_url, 
                       num_output_poses=4, 
                       webhook_url=None, 
                       client_webhook_url=None):
    """Generate poses for a character in a background task.
    
    Args:
        pose_id: UUID of the Pose model instance
        character_image_url: URL of the character image
        num_output_poses: Number of poses to generate
        webhook_url: Webhook URL for Replicate to send updates to
        client_webhook_url: Optional webhook URL to notify client of updates
        
    Returns:
        Dictionary with job status and details
    """
    try:
        # Add a small delay to ensure Redis connection is stable
        time.sleep(2)
        
        # Import here to avoid circular imports
        from image_generation.models import Pose
        
        # Get pose from database
        try:
            pose = Pose.objects.get(id=pose_id)
            pose.status = "processing"
            pose.save()
        except Pose.DoesNotExist:
            logger.error(f"Pose {pose_id} not found")
            return {"status": "error", "message": f"Pose {pose_id} not found"}
        
        # Initialize the Replicate client
        client = ReplicateClient()
        
        # Prepare webhook events filter
        webhook_events_filter = ["start", "output", "completed"]
        
        # Start pose generation
        try:
            result = client.generate_poses(
                character_image_url=character_image_url,
                num_output_poses=num_output_poses,
                webhook_url=webhook_url,
                webhook_events_filter=webhook_events_filter
            )
            
            # Update pose with prediction ID
            pose.replicate_id = result.get("id")
            pose.status = "processing"
            pose.replicate_version = result.get("urls", {}).get("get")
            pose.save()
            
            # Notify client if webhook URL is provided
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "pose_id": str(pose_id),
                        "status": "processing",
                        "message": "Pose generation started"
                    }
                )
            
            return {
                "status": "success",
                "pose_id": str(pose_id),
                "replicate_id": result.get("id"),
                "message": "Pose generation started"
            }
            
        except Exception as e:
            logger.error(f"Error generating poses: {str(e)}")
            
            # Update pose with error status
            pose.status = "failed"
            pose.error_message = str(e)
            pose.save()
            
            # Notify client of error if webhook URL is provided
            if client_webhook_url:
                send_client_webhook(
                    client_webhook_url,
                    {
                        "pose_id": str(pose_id),
                        "status": "failed",
                        "message": f"Error generating poses: {str(e)}"
                    }
                )
            
            # Retry if it's a connection error
            if "Connection" in str(e):
                raise self.retry(exc=e, countdown=10)
                
            return {
                "status": "error",
                "pose_id": str(pose_id),
                "message": f"Error generating poses: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in generate_poses_task: {str(e)}")
        return {
            "status": "error",
            "pose_id": str(pose_id) if pose_id else None,
            "message": f"Unexpected error: {str(e)}"
        }

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def handle_pose_webhook(self, pose_id, payload, client_webhook_url=None):
    """Handle webhook notifications from Replicate for pose generation.
    
    Args:
        pose_id: UUID of the Pose to update
        payload: Webhook payload from Replicate
        client_webhook_url: Optional webhook URL to notify client of updates
        
    Returns:
        Dictionary with processing status
    """
    try:
        # Add a small delay to ensure Redis connection is stable
        time.sleep(1)
        
        # Import here to avoid circular imports
        from image_generation.models import Pose
        
        # Get pose from database
        try:
            pose = Pose.objects.get(id=pose_id)
        except Pose.DoesNotExist:
            logger.error(f"Pose {pose_id} not found")
            return {"status": "error", "message": f"Pose {pose_id} not found"}
        
        # Extract status from payload
        status = payload.get("status")
        
        # Update pose status
        pose.status = status
        
        # If succeeded, extract and save image URLs
        if status == "succeeded":
            output = payload.get("output")
            if output and isinstance(output, list) and len(output) > 0:
                # Extract image URLs from output
                pose.output_urls = output
                logger.info(f"Pose {pose_id} generated successfully with {len(output)} poses")
                
                # Save the first image as the main pose image
                if len(output) > 0:
                    pose.image_url = output[0]
                
                # Save images to storage if needed
                # This could be implemented here or in a separate task
                
            else:
                logger.warning(f"No image URLs in output for pose {pose_id}")
                pose.error_message = "No image URLs in webhook payload"
                
        elif status == "failed":
            # Extract error message if available
            error = payload.get("error")
            if error:
                pose.error_message = error
                logger.error(f"Pose generation {pose_id} failed: {error}")
        
        # Save updates
        pose.save()
        
        # If client webhook URL is provided, send notification
        if client_webhook_url:
            notification_data = {
                "pose_id": str(pose_id),
                "status": status,
                "message": f"Pose generation status updated to {status}"
            }
            
            # Add image URLs if available for succeeded jobs
            if status == "succeeded" and pose.output_urls:
                notification_data["image_urls"] = pose.output_urls
            
            # Add error message for failed jobs
            if status == "failed" and pose.error_message:
                notification_data["error"] = pose.error_message
                
            send_client_webhook(client_webhook_url, notification_data)
        
        return {
            "status": "success",
            "pose_id": str(pose_id),
            "message": f"Updated pose generation status to {status}"
        }
        
    except Exception as e:
        logger.error(f"Error handling pose webhook: {str(e)}")
        
        # Retry if it's a database or connection error
        if "Connection" in str(e) or "database" in str(e).lower():
            raise self.retry(exc=e, countdown=5)
            
        return {
            "status": "error",
            "pose_id": str(pose_id),
            "message": f"Error handling webhook: {str(e)}"
        }
