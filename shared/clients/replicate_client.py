import os
import logging
import requests
from typing import Dict, List, Optional, Any, Union
import replicate
import time
import random
import pathlib
import mimetypes
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

class ReplicateClient:
    """Client for interacting with Replicate API to use AI models"""
    DEFAULT_OWNER_VAR = "REPLICATE_OWNER" # Environment variable for the default owner

    def __init__(self, api_token: Optional[str] = None, owner_override: Optional[str] = None):
        """
        Initialize the Replicate client.
        Allows overriding token and owner, otherwise uses environment variables.

        Args:
            api_token: Specific API token to use. If None, uses REPLICATE_API_TOKEN env var.
            owner_override: Specific owner username to use as default. If None, uses REPLICATE_OWNER env var.
        """
        self.api_token = api_token or os.environ.get("REPLICATE_API_TOKEN")
        self.default_owner = owner_override or os.getenv(self.DEFAULT_OWNER_VAR, "your-replicate-username") # Use override or default env var or fallback

        if not self.api_token:
            logger.warning("No Replicate API token provided. ReplicateClient might not function.")
            self.client = None # Cannot initialize client without token
        else:
            # Initialize the official Replicate client
            try:
                self.client = replicate.Client(api_token=self.api_token)
                # Test connection by getting user info (optional)
                # self.client.users.current()
                logger.info(f"ReplicateClient initialized successfully using token ending: ...{self.api_token[-4:]}")
            except Exception as e:
                logger.error(f"Failed to initialize Replicate client: {e}")
                self.client = None

        # Store model versions (used by specific methods)
        # These might be better defined closer to their usage or passed in
        self.consistent_pose_model_version = "9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772"
        self.lora_trainer_model_version = "c6e78d2501e8088876e99ef21e4460d0dc121af7a4b786b9a4c2d75c620e300d"

        # Base URL and headers for direct requests (kept for methods not yet refactored)
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }

    def generate_character(self, 
                           prompt: str,
                           negative_prompt: str = "",
                           aspect_ratio: str = "1:1",
                           num_outputs: int = 1,
                           output_format: str = "jpg",
                           output_quality: int = 80,
                           seed: Optional[int] = None,
                           safety_tolerance: int = 2,
                           raw: bool = False,
                           webhook: Optional[str] = None, # Added webhook param
                           webhook_events_filter: Optional[List[str]] = None # Added filter param
                           ) -> replicate.prediction.Prediction:
        """
        Generate a character using Flux model via replicate.predictions.create().
        Starts the prediction asynchronously and returns the Prediction object.

        Args:
            prompt: Text prompt for the character
            negative_prompt: Negative text prompt
            aspect_ratio: Aspect ratio (e.g., "1:1", "16:9")
            num_outputs: Number of images to generate
            output_format: Image format ('jpg' or 'png')
            output_quality: Image quality (1-100)
            seed: Random seed
            safety_tolerance: Tolerance level for safety filtering (default: 2)
            raw: Enable raw mode for more authentic photography feel (default: False)
            webhook: Optional webhook URL to receive status updates
            webhook_events_filter: Optional list of event types for webhook
        
        Returns:
            replicate.prediction.Prediction: The prediction object with job ID and tracking info
        """
        if not self.client:
            raise ValueError("Replicate client is not initialized")
            
        # If seed is None, generate a random one
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
            
        # Prepare model parameters
        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": aspect_ratio,
            "seed": seed,
            "num_outputs": num_outputs,
            "output_format": output_format,
            "quality": output_quality,
            "safety_tolerance": safety_tolerance,
            "raw": raw,
            "apply_watermark": False  # Default to no watermark for API use
        }
        
        # Add webhook parameters if provided
        if webhook:
            logger.info(f"Using webhook URL: {webhook}")
            params["webhook"] = webhook
            if webhook_events_filter:
                params["webhook_events_filter"] = webhook_events_filter
        
        # Remove webhook parameters from params dictionary if added previously
        if "webhook" in params:
            del params["webhook"]
        if "webhook_events_filter" in params:
            del params["webhook_events_filter"]
        
        try:
            logger.info(f"Starting character generation with prompt: {prompt[:50]}...")
            
            # Create the prediction using the client
            # For Flux 1.1 Pro, we need to use the version parameter only
            prediction = self.client.predictions.create(
                version="black-forest-labs/flux-1.1-pro",
                input=params,
                webhook=webhook,
                webhook_events_filter=webhook_events_filter
            )
            
            logger.info(f"Character generation job submitted: {prediction.id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error submitting character generation job: {str(e)}")
            raise

    def generate_poses(self, image_url: str = None, image_path: str = None, number_of_outputs: int = 3, **kwargs):
        """
        Generate poses for a character using the FOFR consistent-character model.
        
        Args:
            image_url (str, optional): URL to the input image.
            image_path (str, optional): Path to a local image file to upload.
            number_of_outputs (int): Number of poses to generate (default: 3).
            **kwargs: Additional arguments to pass to the model:
                prompt (str): Text prompt describing the character.
                negative_prompt (str): Things you do not want to see in your image.
                seed (int): Set a seed for reproducibility. Random by default.
                output_format (str): Format of the output images (default: "webp").
                output_quality (int): Quality of the output images, 0-100.
                randomise_poses (bool): Randomise the poses used (default: True).
                disable_safety_checker (bool): Disable safety checker.
                number_of_images_per_pose (int): Images to generate per pose (1-4).
                webhook (str): Webhook URL for status updates.
                webhook_events_filter (list): List of webhook events to filter.
    
        Returns:
            Dict: The prediction.
        """
        if not self.client:
            raise ValueError("Replicate client is not initialized")
        
        # Make sure we have either a URL or a path
        if image_url is None and image_path is None:
            raise ValueError("Either image_url or image_path must be provided")
        
        # Prepare input params
        input_params = {
            "number_of_outputs": number_of_outputs,
            **kwargs  # Include any additional kwargs
        }
        
        # Set image input
        if image_url:
            input_params["subject"] = image_url
        elif image_path:
            # Read file and convert to base64 if needed
            with open(image_path, "rb") as f:
                file_content = f.read()
                
            # For local files, we'll need to open and upload the file
            input_params["subject"] = pathlib.Path(image_path)
        
        # Add webhook if provided
        if "webhook" in kwargs:
            logger.info(f"Using webhook URL: {kwargs['webhook']}")
        
        try:
            # Generate the poses using the model
            logger.info(f"Starting pose generation with {'URL' if image_url else 'local file'}")
            
            # Allow using custom model ID instead of default
            model_id = kwargs.pop('model_id', None)
            model_version = kwargs.pop('model_version', None)
            
            # Determine the full version string to use
            if model_id and model_version:
                # Use the provided model ID and version, combined into the format "owner/model:version"
                logger.info(f"Using custom model: {model_id}:{model_version}")
                version_string = f"{model_id}:{model_version}"
            else:
                # Use the default FOFR consistent-character model with its version
                version_string = "fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772"
            
            # Create the prediction using the version string
            prediction = self.client.predictions.create(
                version=version_string,
                input=input_params,
                webhook=kwargs.get('webhook'),
                webhook_events_filter=kwargs.get('webhook_events_filter')
            )
            
            logger.info(f"Pose generation job submitted: {prediction.id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error submitting pose generation job: {str(e)}")
            raise

    def train_lora(self, training_images: List[str], model_name: str, trigger_word: str, webhook: Optional[str] = None, webhook_events_filter: Optional[List[str]] = None):
        """
        Train a LoRA model using Ostris trainer
        
        Args:
            training_images: List of image URLs for training
            model_name: Name for the trained model
            trigger_word: Trigger word to invoke the model
            webhook: Optional webhook URL to receive status updates
            webhook_events_filter: Optional list of event types for webhook
            
        Returns:
            Dictionary with the trained model ID and status
        """
        if not self.client:
            raise ValueError("Replicate client is not initialized")
            
        # Format the model name to be safe for URLs
        safe_model_name = model_name.lower().replace(" ", "-")
        
        try:
            # Get or create the model
            model_path = f"{self.default_owner}/{safe_model_name}"
            model_info = self.get_or_create_model(safe_model_name)
            
            # Prepare the input
            training_params = {
                "train_data": training_images,
                "instance_prompt": trigger_word,
                "instance_token": trigger_word,
                "max_train_steps": 400  # Keep the default steps low to avoid overfitting
            }
            
            # Add webhook parameters if provided directly to the input params
            if webhook:
                logger.info(f"Using webhook URL: {webhook}")
                training_params["webhook"] = webhook
                if webhook_events_filter:
                    training_params["webhook_events_filter"] = webhook_events_filter
            
            # Submit the training job
            logger.info(f"Starting LoRA training for model {model_name} with {len(training_images)} images...")
            
            # Create the version string in the format "owner/model:version"
            version_string = f"ostris/flux-dev-lora-trainer:{self.lora_trainer_model_version}"
            
            # We need to pass the webhook to the training endpoint using the predictions API
            prediction = self.client.predictions.create(
                version=version_string,
                input=training_params
            )
            
            logger.info(f"LoRA training job submitted: {prediction.id}")
            return {
                "id": prediction.id,
                "status": prediction.status
            }
            
        except Exception as e:
            logger.error(f"Error submitting LoRA training job: {str(e)}")
            raise

    def generate_with_model(self, model_id: str, prompt: str, negative_prompt: str = ""):
        """
        Generate an image using a trained model
        
        Args:
            model_id: ID of the trained model
            prompt: Text prompt (should include the trigger word)
            negative_prompt: Negative text prompt
        
        Returns:
            Dictionary with the generated image URL
        """
        if not self.client:
            raise ValueError("Replicate client is not initialized")
            
        try:
            # Prepare the input
            input_params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt
            }
            
            # Submit the generation job
            logger.info(f"Starting generation with model {model_id} and prompt: {prompt[:50]}...")
            
            # Verify model_id is in the correct format
            if ":" not in model_id:
                raise ValueError("Model ID must include version (e.g., 'owner/model_name:version')")
            
            # The model_id should be in the format "owner/model:version"
            prediction = self.client.predictions.create(
                version=model_id,
                input=input_params
            )
            
            logger.info(f"Generation job submitted: {prediction.id}")
            return {
                "id": prediction.id,
                "status": prediction.status
            }
            
        except Exception as e:
            logger.error(f"Error submitting generation job: {str(e)}")
            raise

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """
        Make a request to the Replicate API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            session = self.create_retry_session()
            
            if method == "GET":
                response = session.get(url, headers=self.headers)
            elif method == "POST":
                response = session.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    def _poll_prediction(self, prediction_id: str):
        """
        Poll for prediction status until it completes
        
        Args:
            prediction_id: Prediction ID to poll
        
        Returns:
            Completed prediction data
        """
        max_polls = 100
        poll_interval = 2  # seconds
        
        for _ in range(max_polls):
            prediction_data = self._make_request("GET", f"predictions/{prediction_id}")
            status = prediction_data.get("status")
            
            if status in ["succeeded", "failed", "canceled"]:
                return prediction_data
                
            time.sleep(poll_interval)
            
        raise TimeoutError(f"Prediction {prediction_id} did not complete in time")

    def get_or_create_model(self, model_name: str, owner: Optional[str] = None):
        """
        Get an existing model or create a new one if it doesn't exist.
        
        Args:
            model_name: Name of the model
            owner: Owner of the model (defaults to self.default_owner if None)
            
        Returns:
            Dict containing model information
        """
        # Use the specified owner or default
        owner = owner or self.default_owner
        model_path = f"{owner}/{model_name}"
        
        # Check if model exists
        model_exists = self._check_if_model_exists(model_path)
        
        if model_exists:
            logger.info(f"Model {model_path} already exists")
            return {
                "name": model_path,
                "created": False
            }
        else:
            # Model doesn't exist, create it
            logger.info(f"Model {model_path} doesn't exist, creating...")
            
            # Create a descriptive name for the model
            safe_model_name = model_name.replace("-", " ").title()
            model_description = f"LoRA fine-tuned model for {safe_model_name}, created via the podcast-generator API"
            
            # Create the model
            model_info = self._create_model(model_path, model_description)
            return model_info

    def finetune_lora(self, 
        model_name: str,
        trigger_word: str,
        input_image_urls: List[str],
        image_processor: str = "crop-and-resize",
        training_prefix: str = "your-replicate-username/flux-trainer",
        training_type: str = "photobooth",
        num_train_epochs: int = 200,
        train_text_encoder: bool = True,
        lora_unet_rank: int = 16,
        lora_text_encoder_rank: int = 8,
        resolution: str = "512",
        lora_rank: int = 16,
        learning_rate: float = 0.0004,
        batch_size: int = 1,
        webhook: Optional[str] = None,
        webhook_events_filter: Optional[List[str]] = None
    ):
        """
        Fine-tune a LoRA model using the Ostris trainer
        
        Args:
            model_name: Name for the LoRA model
            trigger_word: Trigger word for the model
            input_image_urls: List of URLs to images for training
            image_processor: How to process the images ("crop-and-resize" or "auto-orient")
            training_prefix: Prefix for the training model
            training_type: Type of training ("photobooth" or "standard")
            num_train_epochs: Number of training epochs
            train_text_encoder: Whether to train the text encoder
            lora_unet_rank: LoRA rank for UNet
            lora_text_encoder_rank: LoRA rank for text encoder
            resolution: Image resolution for training
            lora_rank: Overall LoRA rank
            learning_rate: Learning rate for training
            batch_size: Batch size for training
            webhook: Webhook URL for status updates
            webhook_events_filter: List of webhook events to filter
            
        Returns:
            Dict: Training information
        """
        try:
            logger.info(f"Starting LoRA fine-tuning for {model_name} with {len(input_image_urls)} images")
            
            # Format the model name to be safe for API use
            safe_model_name = model_name.lower().replace(" ", "-")
            
            # Check if the model exists already and create if needed
            destination = f"{self.default_owner}/{safe_model_name}"
            model_info = self.get_or_create_model(safe_model_name)
            
            # Prepare the training parameters
            training_params = {
                "input_images": input_image_urls,
                "model_name": model_name,
                "trigger_word": trigger_word,
                "destination": destination,
                "training_prefix": training_prefix,
                "training_type": training_type,
                "image_processor": image_processor,
                "num_train_epochs": num_train_epochs,
                "train_text_encoder": train_text_encoder,
                "lora_unet_rank": lora_unet_rank,
                "lora_text_encoder_rank": lora_text_encoder_rank,
                "resolution": resolution,
                "lora_rank": lora_rank,
                "learning_rate": learning_rate,
                "batch_size": batch_size,
            }
            
            # Add webhook parameters if provided
            if webhook:
                # Ensure the webhook URL uses https
                if webhook.startswith("http://"):
                    webhook = webhook.replace("http://", "https://")
                    logger.warning(f"Webhook URL changed from HTTP to HTTPS to comply with Replicate requirements")
                    
                logger.info(f"Using webhook URL: {webhook}")
                training_params["webhook"] = webhook
                
                if webhook_events_filter:
                    # Ensure only valid webhook event types are included
                    valid_events = ["start", "output", "logs", "completed"]
                    filtered_events = [evt for evt in webhook_events_filter if evt in valid_events]
                    
                    if len(filtered_events) != len(webhook_events_filter):
                        logger.warning(f"Some webhook event types were invalid and removed. Valid types: {valid_events}")
                        
                    training_params["webhook_events_filter"] = filtered_events
            
            # Create the version string in the format "owner/model:version"
            version_string = f"ostris/flux-dev-lora-trainer:{self.lora_trainer_model_version}"
            
            # Create the training job using the newer predictions API
            # This is more reliable than the older trainings API
            prediction = self.client.predictions.create(
                version=version_string,
                input=training_params
            )
            
            logger.info(f"LoRA fine-tuning job submitted with ID: {prediction.id}")
            
            return {
                "id": prediction.id,
                "status": prediction.status,
                "destination": destination,
                "model_created": model_info["created"]
            }
            
        except Exception as e:
            logger.error(f"Error creating LoRA fine-tuning: {str(e)}")
            raise

    def _check_if_model_exists(self, model_path: str) -> bool:
        """
        Check if a model exists in Replicate.
        
        Args:
            model_path: The model path in format "owner/model_name"
            
        Returns:
            bool: True if the model exists, False otherwise
        """
        try:
            url = f"https://api.replicate.com/v1/models/{model_path}"
            headers = {"Authorization": f"Token {self.api_token}"}
            
            # Use retry session for better reliability
            session = self.create_retry_session()
            response = session.get(url, headers=headers)
            
            # If 200, model exists
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking if model exists: {str(e)}")
            # Return False so we'll try to create it
            return False
            
    def _create_model(self, model_path: str, model_description: str) -> Dict:
        """
        Create a new model in Replicate.
        
        Args:
            model_path: The model path in format "owner/model_name"
            model_description: Description of the model
            
        Returns:
            dict: The created model information
        """
        try:
            # Extract owner and name from path
            parts = model_path.split('/')
            if len(parts) != 2:
                raise ValueError(f"Invalid model path: {model_path}. Must be in format 'owner/name'")
            
            owner, name = parts
            
            # Use the replicate client directly
            import replicate
            
            # Ensure the API token is set
            replicate.api_token = self.api_token
            
            logger.info(f"Creating model {name} for owner {owner}")
            
            # Create the model using the client library
            model = replicate.models.create(
                name=name,
                description=model_description,
                visibility="public"
            )
            
            logger.info(f"Model created successfully: {model.name}")
            return {"name": model.name, "owner": owner, "created": True}
            
        except Exception as e:
            logger.error(f"Error creating model: {str(e)}")
            
            # Even if model creation fails, we should try to continue with training
            # as the model might actually exist or be created automatically by the training API
            logger.warning(f"Will attempt to continue with training despite model creation failure")
            return {"name": model_path, "created": False}

    def create_retry_session(self, retries=5, backoff_factor=0.5):
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def get_training_status(self, training_id: str) -> dict:
        """
        Get the current status of a training job from Replicate.
        
        Args:
            training_id: The Replicate training ID
        
        Returns:
            dict: Training job information including status
        """
        url = f"https://api.replicate.com/v1/trainings/{training_id}"
        headers = {"Authorization": f"Token {self.api_token}"}
        
        # Use retry session for better reliability
        session = self.create_retry_session()
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()