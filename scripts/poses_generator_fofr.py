#!/usr/bin/env python3
"""
Test script for generating poses from character images using direct URLs

python poses_generator.py --image-url "https://aicc.nyc3.cdn.digitaloceanspaces.com/character_generation/output/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f.jpg"
   
"""

import os
import sys
import json
import time
import random
import argparse
import logging
import requests
import zipfile
from typing import List, Dict, Optional, Any
import pathlib
from urllib.parse import urlparse
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from botocore.client import Config
from botocore.exceptions import ClientError
from pathlib import Path
import boto3
import re
import psycopg2
from django.conf import settings

# Add the project root to the path so we can import Django settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Django settings after setting up the path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Base URL for the API
BASE_URL = "https://example.com/api"  # http://146.190.69.117/api
SERVER_BASE = "https://example.com"    # http://146.190.69.117
# Direct Replicate API URL (for when we don't want to use the server)
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
HEADERS = {'Content-Type': 'application/json'}
TIMEOUT_SECONDS = 120  # Longer timeout for pose generation

# DO Spaces configuration
DO_SPACES_KEY = os.environ.get('DO_SPACES_KEY')
DO_SPACES_SECRET = os.environ.get('DO_SPACES_SECRET')
DO_SPACES_ENDPOINT = os.environ.get('DO_SPACES_ENDPOINT')
DO_SPACES_BUCKET = os.environ.get('DO_SPACES_BUCKET')
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('POSTGRES_DB', 'ai_image_gen')
DB_USER = os.environ.get('POSTGRES_USER', 'ai_image_gen_user')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'aaaa1234')

def get_db_connection():
    """Get a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        return None

def save_to_database(character_id, base_name, prediction_id, image_url, prompt, 
                    negative_prompt, seed, number_of_outputs, output_format, 
                    output_quality, randomise_poses, disable_safety_checker, 
                    number_of_images_per_pose, poses_data, zip_url):
    """Save pose generation data to the database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Insert into pose_generation table
        insert_query = """
        INSERT INTO pose_generation 
        (character_id, base_name, prediction_id, source_image, prompt, negative_prompt, 
        seed, number_of_outputs, output_format, output_quality, randomise_poses, 
        disable_safety_checker, number_of_images_per_pose, zip_url, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        cursor.execute(insert_query, (
            character_id, base_name, prediction_id, image_url, prompt, 
            negative_prompt, seed, number_of_outputs, output_format, 
            output_quality, randomise_poses, disable_safety_checker, 
            number_of_images_per_pose, zip_url, datetime.now()
        ))
        
        generation_id = cursor.fetchone()[0]
        
        # Insert each pose into pose_images table
        for pose in poses_data:
            insert_pose_query = """
            INSERT INTO pose_images
            (generation_id, pose_number, replicate_url, spaces_url, local_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_pose_query, (
                generation_id,
                pose.get('pose_number'),
                pose.get('replicate_url'),
                pose.get('spaces_url'),
                pose.get('local_path'),
                datetime.now()
            ))
        
        conn.commit()
        print(f"✅ Saved generation data to database (ID: {generation_id})")
        return True
    
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

def get_s3_client():
    """Initialize and return an S3 client for DO Spaces"""
    return boto3.client(
        's3',
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
        config=Config(signature_version='s3v4')
    )

def upload_to_spaces(local_file_path, object_key):
    """Upload a file to DO Spaces"""
    try:
        s3 = get_s3_client()
        print(f"Uploading {local_file_path} to {DO_SPACES_BUCKET}/{object_key}")
        
        content_type = 'image/jpeg'
        if local_file_path.lower().endswith('.png'):
            content_type = 'image/png'
        elif local_file_path.lower().endswith('.webp'):
            content_type = 'image/webp'
        elif local_file_path.lower().endswith('.zip'):
            content_type = 'application/zip'
        
        with open(local_file_path, 'rb') as file_data:
            s3.upload_fileobj(
                file_data,
                DO_SPACES_BUCKET,
                object_key,
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': content_type
                }
            )
        print(f"✅ Uploaded file to DO Spaces: {object_key}")
        
        # Generate URLs
        region = DO_SPACES_ENDPOINT.split('.')[0].split('://')[-1]
        origin_url = f"https://{DO_SPACES_BUCKET}.{region}.digitaloceanspaces.com/{object_key}"
        cdn_url = f"https://{DO_SPACES_BUCKET}.{region}.cdn.digitaloceanspaces.com/{object_key}"
        
        return {
            "success": True,
            "origin_url": origin_url,
            "cdn_url": cdn_url
        }
    except Exception as e:
        print(f"❌ Failed to upload to DO Spaces: {str(e)}")
        return {"success": False, "error": str(e)}

def check_file_in_spaces(object_key):
    """Check if a file exists in DO Spaces"""
    try:
        s3 = get_s3_client()
        s3.head_object(Bucket=DO_SPACES_BUCKET, Key=object_key)
        
        # Generate URLs
        region = DO_SPACES_ENDPOINT.split('.')[0].split('://')[-1]
        origin_url = f"https://{DO_SPACES_BUCKET}.{region}.digitaloceanspaces.com/{object_key}"
        cdn_url = f"https://{DO_SPACES_BUCKET}.{region}.cdn.digitaloceanspaces.com/{object_key}"
        
        return {
            "exists": True,
            "origin_url": origin_url,
            "cdn_url": cdn_url
        }
    except ClientError:
        return {"exists": False}
    except Exception as e:
        print(f"❌ Error checking DO Spaces: {str(e)}")
        return {"exists": False, "error": str(e)}

def extract_base_name(image_path):
    """Extract a base name for output files from an image path"""
    # Try to extract filename without extension
    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]
    
    # If it's a URL, extract the last part of the path
    if image_path.startswith(('http://', 'https://')):
        parsed_url = urlparse(image_path)
        path_parts = parsed_url.path.split('/')
        if path_parts and path_parts[-1]:
            filename = path_parts[-1]
            base_name = os.path.splitext(filename)[0]
    
    # If base name is still empty or too generic, use a random ID
    if not base_name or base_name in ('image', 'output', 'file'):
        import uuid
        base_name = f"character_{uuid.uuid4().hex[:8]}"
    
    return base_name

def extract_character_id(image_path):
    """Extract character ID from a path or URL if present"""
    # Try to match UUID format
    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', image_path)
    if match:
        return match.group(1)
    return None

def create_zip_archive(pose_files, zip_path):
    """Create a zip archive of all pose files"""
    try:
        print(f"Creating zip archive: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pose_file in pose_files:
                # Add file to zip
                filename = os.path.basename(pose_file)
                zipf.write(pose_file, filename)
                print(f"  Added {filename} to zip")
        
        print(f"✅ Created zip archive: {zip_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating zip archive: {str(e)}")
        return False

def generate_poses_direct(
    image_url, 
    prompt="Standing pose, full body",
    number_of_outputs=3,
    seed=None,
    negative_prompt=None,
    output_format="jpg",
    output_quality=80,
    randomise_poses=True,
    disable_safety_checker=False,
    number_of_images_per_pose=1,
    save_dir=None
):
    """Generate poses for a character image using Replicate API directly"""
    if not REPLICATE_API_TOKEN:
        print("❌ REPLICATE_API_TOKEN is not set in environment variables.")
        return None
    
    # Generate random seed if not provided
    if seed is None:
        seed = random.randint(1, 2147483647)
        print(f"Using random seed: {seed}")
    
    # Create a base name for output files
    base_name = extract_base_name(image_url)
    print(f"Using base name: {base_name}")
    
    # Use Django's media root if save_dir not provided
    if save_dir is None:
        save_dir = os.path.join(settings.MEDIA_ROOT, "pose_generation/output")
    
    # Create character-specific directory
    char_dir = os.path.join(save_dir, base_name)
    os.makedirs(char_dir, exist_ok=True)
    print(f"Created directory: {char_dir}")
    
    # Consistent Character model ID
    model_id = "fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772"
    
    # Construct the payload for Replicate API
    payload = {
        "version": model_id.split(':')[1],
        "input": {
            "subject": image_url,
            "prompt": prompt,
            "number_of_outputs": min(max(1, number_of_outputs), 20),
            "seed": seed,
            "output_format": output_format,
            "output_quality": output_quality,
            "randomise_poses": randomise_poses,
            "number_of_images_per_pose": min(max(1, number_of_images_per_pose), 4)
        }
    }
    
    # Add optional parameters
    if negative_prompt:
        payload["input"]["negative_prompt"] = negative_prompt
    
    if disable_safety_checker:
        payload["input"]["disable_safety_checker"] = True
    
    # Set up headers with auth token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {REPLICATE_API_TOKEN}"
    }
    
    try:
        print("Sending request to Replicate API directly...")
        print(f"Image URL: {image_url}")
        print(f"Prompt: {prompt}")
        print(f"Number of outputs: {number_of_outputs}")
        
        # Step 1: Create the prediction
        response = requests.post(
            REPLICATE_API_URL, 
            headers=headers, 
            json=payload,
            timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        prediction = response.json()
        prediction_id = prediction.get("id")
        
        if not prediction_id:
            print("❌ Failed to start prediction")
            return None
        
        print(f"✅ Prediction started: {prediction_id}")
        print("Waiting for prediction to complete...")
        
        # Step 2: Poll for completion
        while True:
            poll_url = f"{REPLICATE_API_URL}/{prediction_id}"
            poll_response = requests.get(poll_url, headers=headers, timeout=TIMEOUT_SECONDS)
            poll_response.raise_for_status()
            prediction_status = poll_response.json()
            
            status = prediction_status.get("status")
            print(f"Status: {status}")
            
            if status == "succeeded":
                break
            elif status in ("failed", "canceled"):
                print(f"❌ Prediction failed: {prediction_status.get('error')}")
                return None
            
            # Wait before polling again
            import time
            time.sleep(5)
        
        # Get the output URLs
        output_urls = prediction_status.get("output", [])
        if not output_urls:
            print("❌ No output URLs in the response")
            return None
        
        print(f"✅ Successfully generated {len(output_urls)} poses!")
        
        # Process each generated pose
        pose_results = []
        local_pose_files = []  # Track local file paths for zip creation
        
        for i, pose_url in enumerate(output_urls):
            print(f"\nPose {i+1}:")
            print(f"Replicate URL: {pose_url}")
            
            # Create output filename
            pose_filename = f"{base_name}-pose-{i+1}.{output_format}"
            local_file_path = os.path.join(char_dir, pose_filename)
            
            # Download the pose image from Replicate
            print(f"Downloading pose to: {local_file_path}")
            response = requests.get(pose_url, stream=True, timeout=TIMEOUT_SECONDS)
            
            if response.status_code != 200:
                print(f"❌ Failed to download pose: HTTP {response.status_code}")
                continue
                
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded pose to: {local_file_path}")
            local_pose_files.append(local_file_path)
            
            # Define the object key for DO Spaces
            pose_space_key = f"pose_generation/output/{base_name}/{pose_filename}"
            
            # Check if file already exists in DO Spaces
            spaces_check = check_file_in_spaces(pose_space_key)
            
            if spaces_check["exists"]:
                print(f"✅ Pose already exists in DO Spaces: {pose_space_key}")
                print(f"  Origin URL: {spaces_check['origin_url']}")
                print(f"  CDN URL: {spaces_check['cdn_url']}")
                spaces_url = spaces_check["cdn_url"]
            else:
                # Upload to DO Spaces if it doesn't exist
                print(f"Uploading pose to DO Spaces...")
                upload_result = upload_to_spaces(local_file_path, pose_space_key)
                
                if upload_result["success"]:
                    print(f"✅ Uploaded pose to DO Spaces")
                    print(f"  Origin URL: {upload_result['origin_url']}")
                    print(f"  CDN URL: {upload_result['cdn_url']}")
                    spaces_url = upload_result["cdn_url"]
                else:
                    spaces_url = None
                
            # Save metadata for this pose
            pose_metadata = {
                "pose_number": i+1,
                "local_path": local_file_path,
                "replicate_url": pose_url,
                "spaces_url": spaces_url,
                "space_key": pose_space_key
            }
            
            pose_results.append(pose_metadata)
        
        # Create a zip file with all poses
        zip_filename = f"{base_name}-poses.zip"
        zip_path = os.path.join(char_dir, zip_filename)
        create_zip_archive(local_pose_files, zip_path)
        
        # Upload zip file to DO Spaces
        zip_space_key = f"pose_generation/output/{base_name}/{zip_filename}"
        zip_upload_result = upload_to_spaces(zip_path, zip_space_key)
        
        if zip_upload_result["success"]:
            print(f"✅ Uploaded zip to DO Spaces")
            print(f"  Origin URL: {zip_upload_result['origin_url']}")
            print(f"  CDN URL: {zip_upload_result['cdn_url']}")
            zip_url = zip_upload_result["cdn_url"]
        else:
            zip_url = None
        
        # Save generation parameters to a JSON file
        params_path = os.path.join(char_dir, f"{base_name}-poses-params.json")
        
        params_data = {
            "base_name": base_name,
            "source_image": image_url,
            "generation_parameters": {
                "prompt": prompt,
                "seed": seed,
                "negative_prompt": negative_prompt,
                "output_format": output_format,
                "output_quality": output_quality,
                "randomise_poses": randomise_poses,
                "disable_safety_checker": disable_safety_checker,
                "number_of_outputs": number_of_outputs,
                "number_of_images_per_pose": number_of_images_per_pose
            },
            "replicate_prediction_id": prediction_id,
            "poses": pose_results,
            "zip_file": {
                "local_path": zip_path,
                "space_key": zip_space_key,
                "spaces_url": zip_url
            }
        }
        
        with open(params_path, 'w') as f:
            json.dump(params_data, f, indent=2)
        
        print(f"\n✅ Saved generation parameters to: {params_path}")
        
        # Save to database
        character_id = extract_character_id(image_url)
        save_to_database(
            character_id=character_id,
            base_name=base_name,
            prediction_id=prediction_id,
            image_url=image_url,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            number_of_outputs=number_of_outputs,
            output_format=output_format,
            output_quality=output_quality,
            randomise_poses=randomise_poses,
            disable_safety_checker=disable_safety_checker,
            number_of_images_per_pose=number_of_images_per_pose,
            poses_data=pose_results,
            zip_url=zip_url
        )
        
        return {
            "base_name": base_name,
            "source_image": image_url,
            "prediction_id": prediction_id,
            "num_poses_requested": number_of_outputs,
            "num_poses_generated": len(pose_results),
            "seed": seed,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "poses": pose_results,
            "zip_file": {
                "local_path": zip_path,
                "spaces_url": zip_url
            },
            "params_file": params_path
        }
        
    except Exception as e:
        print(f"❌ Error generating poses: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def generate_poses_via_api(image_url, prompt, negative_prompt='', seed=42, 
                          number_of_outputs=3, output_format='webp', output_quality=80, 
                          randomise_poses=True, disable_safety_checker=False, 
                          number_of_images_per_pose=1, save_dir=None,
                          client_webhook_url=None):
    """
    Generate poses via the API.
    
    image_url: URL of the image to use as the base for pose generation
    prompt: Text prompt to guide pose generation
    negative_prompt: Negative text prompt to guide pose generation
    seed: Random seed for reproducibility
    number_of_outputs: Number of poses to generate
    output_format: Output format (webp, jpg, png)
    output_quality: Output quality (0-100)
    randomise_poses: Whether to randomise poses
    disable_safety_checker: Whether to disable the safety checker
    number_of_images_per_pose: Number of images to generate per pose
    save_dir: Directory to save poses to
    client_webhook_url: URL to receive webhook notifications
    
    Returns: API response data
    """
    if not client_webhook_url:
        print("WARNING: No webhook URL provided. Status updates won't be received.")
        print("Consider adding a webhook URL for better status tracking.")
    
    try:
        # Step 1: First create a character with the image URL as subject
        character_endpoint = f"{BASE_URL}/image-generation/generate/"
        
        # Prepare the character payload
        character_payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "subject": image_url,  # Use 'subject' instead of 'image_prompt'
            "output_format": output_format,
            "output_quality": output_quality,
            "number_of_outputs": 1  # We only need one character image
        }
        
        # Add client webhook URL if provided
        if client_webhook_url:
            character_payload["client_webhook_url"] = client_webhook_url
        
        # Send the character creation request
        print(f"\n============ STEP 1: CHARACTER GENERATION ============")
        print(f"Endpoint: {character_endpoint}")
        print(f"Payload: {json.dumps(character_payload, indent=2)}")
        print(f"Headers: {HEADERS}")
        
        try:
            character_response = requests.post(
                character_endpoint, 
                json=character_payload, 
                headers=HEADERS, 
                timeout=TIMEOUT_SECONDS
            )
            
            # Print the response content for debugging
            print(f"\nResponse Status: {character_response.status_code}")
            print(f"Response Headers: {dict(character_response.headers)}")
            print(f"Response Content: {character_response.text}")
            
            character_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Error in character creation request: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Status: {e.response.status_code}")
                print(f"Response Content: {e.response.text}")
            raise
        
        # Parse the character response
        character_data = character_response.json()
        character_id = character_data.get('id')
        replicate_prediction_id = character_data.get('replicate_prediction_id')
        
        if not character_id:
            raise ValueError("No character ID returned from API")
            
        print(f"\nCharacter created with ID: {character_id}")
        if replicate_prediction_id:
            print(f"Replicate Prediction ID: {replicate_prediction_id}")
            print(f"Replicate Prediction Link: https://replicate.com/p/{replicate_prediction_id}")
        
        # Wait for just a few seconds to confirm job is processing
        # This doesn't wait for full character generation, just checks initial status
        character_status_endpoint = f"{BASE_URL}/image-generation/status/{character_id}/"
        max_retries = 3  # Reduced number of retries, we just want to check initial status
        retry_count = 0
        
        while retry_count < max_retries:
            time.sleep(2)  # Wait before checking status
            
            try:
                status_response = requests.get(
                    character_status_endpoint, 
                    headers=HEADERS, 
                    timeout=TIMEOUT_SECONDS
                )
                
                print(f"\nInitial status check {retry_count+1}/{max_retries}")
                print(f"Status Response: {status_response.status_code}")
                print(f"Status Content: {status_response.text}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get('status')
                    print(f"Character Status: {current_status}")
                    
                    # If we get the replicate_prediction_id, we're good to proceed
                    if not replicate_prediction_id and status_data.get('replicate_prediction_id'):
                        replicate_prediction_id = status_data.get('replicate_prediction_id')
                        print(f"Got Replicate Prediction ID: {replicate_prediction_id}")
                        print(f"Replicate Prediction Link: https://replicate.com/p/{replicate_prediction_id}")
                    
                    # If there's an error status, report it
                    if current_status in ['failed', 'error']:
                        error_message = status_data.get('error_message', 'Unknown error')
                        print(f"Character generation reported error: {error_message}")
                        print("Will attempt to proceed with poses generation anyway...")
                    
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"\n❌ Error checking initial character status: {str(e)}")
                # Continue even if status check fails - character might still be processing
            
            retry_count += 1
        
        print(f"\nProceeding to pose generation without waiting for character generation completion.")
        print(f"Status updates will be delivered via webhook if provided.")
        
        # Step 2: Now generate poses with the character ID
        poses_endpoint = f"{BASE_URL}/image-generation/generate/poses/"
        
        # Prepare the poses payload
        poses_payload = {
            "character_id": character_id,
            "pose_prompt": prompt,
            "seed": seed,
            "output_format": output_format,
            "output_quality": output_quality,
            "number_of_outputs": number_of_outputs  # Set the number of poses to generate
        }
        
        # Add optional parameters if needed
        if randomise_poses:
            poses_payload["randomise_poses"] = randomise_poses
            
        if disable_safety_checker:
            poses_payload["disable_safety_checker"] = disable_safety_checker
            
        if number_of_images_per_pose > 1:
            poses_payload["number_of_images_per_pose"] = number_of_images_per_pose
            
        # Add client webhook URL if provided
        if client_webhook_url:
            poses_payload["client_webhook_url"] = client_webhook_url
        
        # Send the API request
        print(f"\n============ STEP 2: POSE GENERATION ============")
        print(f"Endpoint: {poses_endpoint}")
        print(f"Payload: {json.dumps(poses_payload, indent=2)}")
        
        try:
            response = requests.post(
                poses_endpoint, 
                json=poses_payload, 
                headers=HEADERS, 
                timeout=TIMEOUT_SECONDS
            )
            
            # Print the response content for debugging
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Content: {response.text}")
            
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Error in pose generation request: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Status: {e.response.status_code}")
                print(f"Response Content: {e.response.text}")
            raise
        
        # Parse the response data
        data = response.json()
        
        # Extract information from the response
        pose_id = data.get('id')
        status = data.get('status')
        replicate_prediction_id = data.get('replicate_prediction_id')
        
        print(f"\n✅ Pose generation job submitted successfully!")
        print(f"Prompt: {prompt}")
        print(f"Job ID: {pose_id}")
        if replicate_prediction_id:
            print(f"Replicate Prediction ID: {replicate_prediction_id}")
            print(f"Replicate Prediction Link: https://replicate.com/p/{replicate_prediction_id}")
        print(f"Initial Status: {status}")
        
        # Display client webhook URL if provided
        if client_webhook_url:
            print(f"Client Webhook URL: {client_webhook_url}")
            print("Status updates will be sent to your webhook URL when the job status changes")
        
        print("\nFull API Response:")
        print(json.dumps(data, indent=2))
        
        return data
    
    except Exception as e:
        print(f"❌ Error generating poses via API: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n❌ Pose generation failed.")
        return None

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate poses from a character image")
    parser.add_argument("--image-url", dest="image_url", required=True, help="URL to the character image")
    parser.add_argument("--prompt", dest="prompt", default="Generate different poses of this character", help="Prompt for pose generation")
    parser.add_argument("--negative-prompt", dest="negative_prompt", default="bad anatomy, blurry, low quality", help="Negative prompt for pose generation")
    parser.add_argument("--seed", dest="seed", type=int, default=42, help="Random seed for generation")
    parser.add_argument("--number-of-outputs", dest="number_of_outputs", type=int, default=3, help="Number of poses to generate")
    parser.add_argument("--output-format", dest="output_format", choices=["webp", "jpg", "png"], default="webp", help="Output format")
    parser.add_argument("--output-quality", dest="output_quality", type=int, default=80, help="Output quality (0-100)")
    parser.add_argument("--save-dir", dest="save_dir", default=None, help="Directory to save poses to (default: Django MEDIA_ROOT/pose_generation/output)")
    parser.add_argument("--randomise-poses", dest="randomise_poses", action="store_true", help="Randomise poses")
    parser.add_argument("--disable-safety-checker", dest="disable_safety_checker", action="store_true", help="Disable safety checker")
    parser.add_argument("--number-of-images-per-pose", dest="number_of_images_per_pose", type=int, default=1, help="Number of images to generate per pose")
    parser.add_argument("--client-webhook-url", dest="client_webhook_url", help="Optional client webhook URL for status updates")
    parser.add_argument("--use-api", dest="use_api", action="store_true", help="Use the API instead of direct Replicate access")
    
    args = parser.parse_args()
    
    if args.save_dir is None:
        # Default to Django's media root
        try:
            save_dir = os.path.join(settings.MEDIA_ROOT, "pose_generation/output")
            print(f"Using Django MEDIA_ROOT: {save_dir}")
        except Exception as e:
            # Fallback if Django settings aren't available
            save_dir = "./media/pose_generation/output"
            print(f"Django settings not available. Using fallback directory: {save_dir}")
    else:
        save_dir = args.save_dir
        
    # Create the save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Generate the poses
    if args.use_api:
        # Use the API (hitting the Django endpoint)
        result = generate_poses_via_api(
            image_url=args.image_url,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            seed=args.seed,
            number_of_outputs=args.number_of_outputs,
            output_format=args.output_format,
            output_quality=args.output_quality,
            randomise_poses=args.randomise_poses,
            disable_safety_checker=args.disable_safety_checker,
            number_of_images_per_pose=args.number_of_images_per_pose,
            save_dir=save_dir,
            client_webhook_url=args.client_webhook_url
        )
    else:
        # Use direct Replicate access
        result = generate_poses_direct(
            image_url=args.image_url,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            seed=args.seed,
            number_of_outputs=args.number_of_outputs,
            output_format=args.output_format,
            output_quality=args.output_quality,
            randomise_poses=args.randomise_poses,
            disable_safety_checker=args.disable_safety_checker,
            number_of_images_per_pose=args.number_of_images_per_pose,
            save_dir=save_dir
        )
    
    # Print results
    if result:
        print("\nGeneration completed successfully!")
        
        # Print paths to saved files
        character_id = result.get("base_name", "")
        if character_id:
            print(f"\nFile Locations:")
            print(f"- Local directory: {save_dir}/{character_id}/")
            print(f"- Local zip file: {save_dir}/{character_id}/{character_id}-poses.zip")
            
            # Print Digital Ocean URLs if available
            zip_url = result.get("zip_file", {}).get("spaces_url")
            if zip_url:
                print(f"- DO Spaces zip URL: {zip_url}")
                print(f"\nUse this URL for fine-tuning with the LoRA script:")
                print(f"{zip_url}")
    else:
        print("\n❌ Generation failed.")