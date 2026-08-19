import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import uuid
from urllib.parse import urlparse, urljoin
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import psycopg2
from psycopg2.extras import Json
import sys
import logging
import re
import argparse
import time


# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# Update to use the new modular API structure
API_URL = "https://example.com/api/image-generation/finetuned/lora/flux-1/" # Updated to image-generation app endpoint
REPLICATE_OWNER = os.environ.get("REPLICATE_OWNER", "your-replicate-username")
LORA_MODEL_ID = "468cf79a-a1bf-4f4e-ac54-84aeb562ce8f"
LORA_MODEL_VERSION = "cb28ff88f564c9467fede8aebf088fcdcdcb51e232c7227276b5d2afdae919dc"
LORA_MODEL_FULL_ID = f"{REPLICATE_OWNER}/{LORA_MODEL_ID}:{LORA_MODEL_VERSION}"
DOWNLOADS_DIR = Path("./downloads")

# DO Spaces configuration
DO_SPACES_KEY = os.environ.get("DO_SPACES_KEY")
DO_SPACES_SECRET = os.environ.get("DO_SPACES_SECRET")
DO_SPACES_ENDPOINT = os.environ.get("DO_SPACES_ENDPOINT")
DO_SPACES_BUCKET = os.environ.get("DO_SPACES_BUCKET")

# Postgres configuration
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger()

# Use the trigger word in the prompt for best results
TRIGGER_WORD = "468cf79a-a1bf-4f4e-ac54-84aeb562ce8f"
PROMPT = f"Ultra-detailed portrait of {TRIGGER_WORD} in a futuristic setting, 8K resolution, photorealistic"
NUM_OUTPUTS = 4
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, bad anatomy, deformed features"
DEFAULT_PROMPT = f"Ultra-detailed portrait of {TRIGGER_WORD} in a futuristic setting, 8K resolution, photorealistic"

def extract_model_name(model_id):
    """Extract just the model name/hash part from a full model ID.
    
    Examples:
    - 'your-replicate-username/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f:version' -> '468cf79a-a1bf-4f4e-ac54-84aeb562ce8f'
    - '468cf79a-a1bf-4f4e-ac54-84aeb562ce8f' -> '468cf79a-a1bf-4f4e-ac54-84aeb562ce8f'
    """
    # Pattern to match UUID format
    uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    match = re.search(uuid_pattern, model_id)
    if match:
        return match.group(1)
    
    # If it doesn't match a UUID pattern, try to extract from owner/name:version format
    if '/' in model_id:
        parts = model_id.split('/')
        if len(parts) > 1:
            name_version = parts[1].split(':')
            return name_version[0]
    
    # If all else fails, return the original
    return model_id

def model_name_from_id(model_id):
    """Extract model name from full ID for file naming"""
    parts = model_id.split('/')
    if len(parts) > 1:
        return parts[1].split(':')[0]
    return uuid.uuid4().hex[:8]  # Fallback to random ID

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
        config=Config(signature_version="s3v4")
    )

def upload_to_spaces(local_file_path, object_key):
    try:
        s3 = get_s3_client()
        with open(local_file_path, 'rb') as data:
            s3.upload_fileobj(
                data,
                DO_SPACES_BUCKET,
                object_key,
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'image/jpeg'
                }
            )
        logger.info(f"✅ Uploaded file to DO Spaces: {object_key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to upload to DO Spaces: {e}")
        return False

def save_generation_to_db(payload, model_name, images):
    """
    Save the generation data to the database.
    Updated to work with the new model_training schema.
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    with conn.cursor() as cursor:
        job_id = uuid.uuid4()
        
        # Updated table name to use model_training app prefix
        cursor.execute(
            """
            INSERT INTO model_training_loragenerationjob 
            (id, model_id, prompt, negative_prompt, status, client_webhook_url, output_urls, 
             created_at, updated_at, replicate_prediction_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
            """,
            (
                job_id,
                payload.get('model_id'),
                payload.get('prompt'),
                payload.get('negative_prompt'),
                'succeeded',
                None,  # client_webhook_url
                Json(images) if images else Json([]),
                None  # replicate_prediction_id
            )
        )
        conn.commit()
        logger.info(f"✅ Saved to database with job ID: {job_id}")
        return job_id
    
def generate_images_with_finetuned_model(prompt, model_id=LORA_MODEL_FULL_ID, num_outputs=NUM_OUTPUTS, client_webhook_url=None, aspect_ratio="1:1", width=None, height=None, output_format="webp"):
    """
    Start an image generation job with a fine-tuned model using webhook-based API
    Returns job ID and status information
    
    Parameters:
    - prompt: The text prompt for image generation
    - model_id: The ID of the model to use (default is LORA_MODEL_FULL_ID)
    - num_outputs: Number of images to generate
    - client_webhook_url: Optional URL to receive status updates
    - aspect_ratio: Aspect ratio for generated images ("1:1", "16:9", "4:3", "custom", etc.)
    - width: Custom width when aspect_ratio is "custom"
    - height: Custom height when aspect_ratio is "custom"
    - output_format: Output format for generated images (webp, jpg, png)
    """
    try:
        # Extract the model name (36-character UUID) from the model ID for tracking
        model_name = extract_model_name(model_id)
        
        # Set up payload for generation
        payload = {
            "model_id": model_id,
            "prompt": prompt,
            "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
            "num_outputs": num_outputs,
            "seed": 0,  # 0 means random seed
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "safety_checker": True,
            "scheduler": "DPMSolverMultistep",  # One of: DDIMScheduler, LMSDiscreteScheduler, PNDMScheduler, EulerDiscreteScheduler, EulerAncestralDiscreteScheduler, DPMSolverMultistep
            "aspect_ratio": aspect_ratio,
            "output_format": output_format
        }
        
        # Add width and height if aspect_ratio is custom
        if aspect_ratio == "custom" and width and height:
            payload["width"] = width
            payload["height"] = height
        
        # Add client webhook URL if provided
        if client_webhook_url:
            payload["client_webhook_url"] = client_webhook_url
        
        # Making request to the server
        print(f"\nSending request to {API_URL}...")
        print(f"Model: {model_id}")
        print(f"Prompt: \"{prompt}\"")
        
        start_time = time.time()
        response = requests.post(API_URL, json=payload)
        
        # Parse the response
        if response.status_code in [200, 201, 202]:
            data = response.json()
            job_id = data.get("id")
            job_status = data.get("status")
            replicate_id = data.get("replicate_prediction_id")
            
            # Check if images were generated immediately
            image_urls = data.get("output_urls", [])
            
            # Calculate response time
            response_time = time.time() - start_time
            print(f"Response received in {response_time:.2f} seconds")
            
            # If we got images back immediately, save them
            if image_urls:
                print(f"✅ Images generated immediately! {len(image_urls)} images available.")
                for i, url in enumerate(image_urls):
                    print(f"Image {i+1}: {url}")
            else:
                print(f"✅ Generation job started successfully (Job ID: {job_id})")
                print(f"🔄 Status: {job_status}")
            
            if replicate_id:
                print(f"📊 Replicate prediction: https://replicate.com/p/{replicate_id}")
            else:
                print("📝 Replicate prediction ID not available yet.")

        else:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Additional instructions based on response type
        if not image_urls:
            print("\nThe job is running in the background. You can close this script anytime.")
            print("Status updates will be handled by webhook callbacks.")
        else:
            print("\nJob completed synchronously. Images were generated immediately.")

        return {
            "success": True, 
            "job_id": job_id, 
            "prediction_id": replicate_id,
            "status": job_status
        }

    except Exception as e:
        logger.error("❌ Request failed: %s", str(e))
        return {"success": False, "error": str(e)}

def wait_for_replicate_id(job_id, base_url, max_attempts=20, delay=2):
    """Poll the job status endpoint until a Replicate prediction ID is available."""
    # Fix the URL format - remove trailing slash if it exists
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    status_url = f"{base_url}/{job_id}"
    
    logging.info(f"Checking status URL: {status_url}")
    
    # Wait a bit before first poll to give the server time to update the database
    logging.info(f"Waiting {delay} seconds before first poll...")
    time.sleep(delay)
    
    for attempt in range(max_attempts):
        try:
            logging.info(f"Checking for Replicate ID (attempt {attempt+1}/{max_attempts})...")
            response = requests.get(status_url)
            logging.info(f"Response status code: {response.status_code}")
            
            # Handle success response
            if response.status_code == 200:
                # Print raw response text for debugging
                response_text = response.text
                logging.info(f"Raw response: {response_text}")
                
                try:
                    data = response.json()
                    logging.info(f"Parsed JSON data: {data}")
                    
                    # Check for the prediction ID
                    replicate_id = data.get("replicate_prediction_id")
                    logging.info(f"Extracted replicate_prediction_id: {replicate_id}")
                    
                    if replicate_id:
                        logging.info(f"✅ Received Replicate prediction ID: {replicate_id}")
                        return replicate_id
                except Exception as json_error:
                    logging.error(f"Error parsing JSON: {json_error}")
            # Handle server error - often happens temporarily during Celery processing
            else:
                logging.warning(f"Server returned status code {response.status_code}. This might be temporary while Celery processes the job.")
                
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Error checking job status: {e}")
            time.sleep(delay)
    
    logging.warning("⚠️ Maximum attempts reached. Could not retrieve Replicate prediction ID.")
    
    # Manual fallback - inform the user to check the job manually
    print("\n⚠️ Could not automatically retrieve the Replicate prediction ID.")
    print("The job is likely still running in the background.")
    print(f"You can manually check the job status at: {status_url}")
    print("Or view completed jobs at: https://replicate.com/predictions")
    
    return None

# In the main part of your script:
if __name__ == "__main__":
    # Make sure downloads directory exists
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    # Setup logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate images with fine-tuned LoRA model")
    parser.add_argument("--prompt", type=str, help="Text prompt for image generation", default=DEFAULT_PROMPT)
    parser.add_argument("--negative-prompt", type=str, help="Negative prompt", default=DEFAULT_NEGATIVE_PROMPT)
    parser.add_argument("--count", type=int, help="Number of images to generate", default=NUM_OUTPUTS)
    parser.add_argument("--download", action="store_true", help="Download images when ready")
    parser.add_argument("--aspect-ratio", type=str, help="Aspect ratio for generated images (1:1, 16:9, 4:3, custom, etc.)", default="1:1")
    parser.add_argument("--width", type=int, help="Custom width (used when aspect-ratio is 'custom')")
    parser.add_argument("--height", type=int, help="Custom height (used when aspect-ratio is 'custom')")
    parser.add_argument("--webhook", type=str, help="Optional webhook URL to receive callbacks")
    parser.add_argument("--model-id", type=str, help="Full model ID (e.g., your-replicate-username/model-id:version)", default=LORA_MODEL_FULL_ID)
    parser.add_argument("--output-format", type=str, help="Output format (webp, jpg, png)", default="webp")
    args = parser.parse_args()

    # Add this line to define user_prompt
    user_prompt = args.prompt

    # Start the job and return immediately
    result = generate_images_with_finetuned_model(
        user_prompt, 
        model_id=args.model_id,
        num_outputs=args.count,
        aspect_ratio=args.aspect_ratio,
        width=args.width,
        height=args.height,
        client_webhook_url=args.webhook,
        output_format=args.output_format
    )
 
    # Initialize replicate_id to avoid undefined variable errors
    replicate_id = None

    if result and result.get("success") and result.get("job_id"):
        job_id = result["job_id"]
        
        # Wait for the Replicate prediction ID
        replicate_id = wait_for_replicate_id(
            job_id=job_id,
            base_url=API_URL,  # Just the base URL
            max_attempts=15,  # Try for about 45 seconds
            delay=3
        )
        
        # Print status with or without Replicate ID
        print("\n✅ Job successfully started!")
        print(f"🔍 Check status at: {API_URL}{job_id}/")
        
        if replicate_id:
            print(f"📊 Replicate prediction: https://replicate.com/p/{replicate_id}")
        else:
            print(f"📊 Replicate prediction: N/A (not available yet)")
        
        print("\nThe job is running in the background. You can close this script anytime.")
        print("Status updates will be handled by webhook callbacks.")
    elif result and not result.get("success"):
        print(f"\n❌ Failed to start job: {result.get('error', 'Unknown error')}")
    else:
        print("\n❌ Failed to start job: No valid response received")