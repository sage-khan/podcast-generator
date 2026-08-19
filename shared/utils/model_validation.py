import logging
import re
from typing import Tuple, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

# Regular expressions for model ID validation
REPLICATE_MODEL_ID_PATTERN = r'^([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9]+))?$'
VERSION_ONLY_PATTERN = r'^[a-zA-Z0-9]+$'


def parse_replicate_model_id(model_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse a Replicate model ID in the format "owner/model_name:version"
    
    Args:
        model_id (str): Model ID string in the format "owner/model_name:version" or "owner/model_name"
        
    Returns:
        Tuple[str, str, Optional[str]]: (owner, model_name, version) or (None, None, None) if invalid
    """
    if not model_id:
        return None, None, None
        
    # Check if model_id matches the expected pattern
    match = re.match(REPLICATE_MODEL_ID_PATTERN, model_id)
    if not match:
        # Check if it's a version-only string
        if re.match(VERSION_ONLY_PATTERN, model_id):
            logger.warning(f"Model ID '{model_id}' appears to be a version only. It should be in the format 'owner/model_name:version'")
            return None, None, model_id
        logger.error(f"Invalid model ID format: {model_id}")
        return None, None, None
    
    # Extract the components
    owner = match.group(1)
    model_name = match.group(2)
    version = match.group(3)  # This might be None if no version is specified
    
    return owner, model_name, version


def format_for_replicate_run(owner: str, model_name: str, version: Optional[str] = None) -> str:
    """
    Format owner, model_name, and version for use with replicate.run() method
    
    Args:
        owner (str): Model owner
        model_name (str): Model name
        version (str, optional): Model version
        
    Returns:
        str: Formatted model ID for replicate.run()
    """
    model_id = f"{owner}/{model_name}"
    if version:
        model_id = f"{model_id}:{version}"
    return model_id


def prepare_for_replicate_predictions_create(model_id: str) -> Dict[str, str]:
    """
    Prepare model ID for use with replicate.predictions.create() method
    
    Args:
        model_id (str): Model ID in the format "owner/model_name:version" or "owner/model_name"
        
    Returns:
        Dict[str, str]: Dictionary with model and version keys for predictions.create()
    """
    owner, model_name, version = parse_replicate_model_id(model_id)
    
    if not owner or not model_name:
        raise ValueError(f"Invalid model ID format: {model_id}")
    
    result = {
        "model": f"{owner}/{model_name}"
    }
    
    if version:
        result["version"] = version
    
    return result


def validate_webhook_url(webhook_url: str) -> str:
    """
    Validate and potentially fix a webhook URL for Replicate
    
    Args:
        webhook_url (str): Webhook URL to validate
        
    Returns:
        str: Valid webhook URL (forced to HTTPS)
    """
    if not webhook_url:
        return None
        
    # Ensure the URL uses HTTPS, not HTTP (required by Replicate)
    if webhook_url.startswith('http://'):
        webhook_url = webhook_url.replace('http://', 'https://')
        logger.warning(f"Webhook URL converted to HTTPS: {webhook_url}")
    
    # Add https:// if the URL doesn't start with a scheme
    if not webhook_url.startswith('https://'):
        webhook_url = f"https://{webhook_url}"
        logger.warning(f"Added HTTPS to webhook URL: {webhook_url}")
        
    return webhook_url


def verify_model_exists(model_id: str) -> bool:
    """
    Verify that a model exists on Replicate
    
    Args:
        model_id (str): Model ID in the format "owner/model_name" or "owner/model_name:version"
        
    Returns:
        bool: True if the model exists, False otherwise
    """
    try:
        owner, model_name, version = parse_replicate_model_id(model_id)
        
        if not owner or not model_name:
            logger.error(f"Invalid model ID format: {model_id}")
            return False
            
        # Construct the API URL for the model
        api_url = f"https://api.replicate.com/v1/models/{owner}/{model_name}"
        
        # If version is specified, check that specific version
        if version:
            api_url = f"{api_url}/versions/{version}"
        
        # Make the request
        response = requests.get(api_url)
        
        # Return True if the request was successful
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error verifying model {model_id}: {str(e)}")
        return False


def validate_replicate_model_version_field(field_length: int = 255) -> None:
    """
    Log a warning if the field length for replicate_model_version is too short
    
    Args:
        field_length (int): Current field length in the database
    """
    recommended_length = 255
    
    if field_length < recommended_length:
        logger.warning(
            f"The 'replicate_model_version' field length ({field_length}) may be too short. "
            f"Replicate model version strings can be long. Consider increasing it to at least {recommended_length} characters "
            f"with a database migration."
        )
    else:
        logger.debug(f"The 'replicate_model_version' field length ({field_length}) is adequate.")


def generate_payload_for_replicate(
    model_id: str, 
    input_params: Dict[str, Any], 
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a correctly formatted payload for Replicate API
    
    Args:
        model_id (str): Model ID in the format "owner/model_name:version"
        input_params (Dict[str, Any]): Input parameters for the model
        webhook_url (str, optional): Webhook URL for status updates
        
    Returns:
        Dict[str, Any]: Properly formatted payload for Replicate API
    """
    # Parse the model ID
    owner, model_name, version = parse_replicate_model_id(model_id)
    
    if not owner or not model_name:
        raise ValueError(f"Invalid model ID format: {model_id}")
    
    # Build the base payload
    payload = {
        "model": f"{owner}/{model_name}",
        "input": input_params
    }
    
    # Add version if specified
    if version:
        payload["version"] = version
    
    # Add webhook if specified
    if webhook_url:
        # Ensure webhook URL uses HTTPS
        webhook_url = validate_webhook_url(webhook_url)
        
        # Only include valid webhook URLs
        if webhook_url:
            payload["webhook"] = webhook_url
            # Add webhook events - only use valid event types
            payload["webhook_events_filter"] = ["start", "output", "logs", "completed"]
    
    return payload
