#!/usr/bin/env python3
"""
Test script that checks both local server storage and DO Spaces
"""

import requests
import json
import logging
import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from urllib.parse import urlparse, urljoin
from pathlib import Path
from dotenv import load_dotenv
import secrets
import urllib.parse
import sys
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Load environment variables
load_dotenv()

# Base URL for the API
BASE_URL = os.environ.get("API_URL", "https://example.com")
SERVER_BASE = "https://example.com"
HEADERS = {'Content-Type': 'application/json'}
TIMEOUT_SECONDS = 60

# DO Spaces configuration
DO_SPACES_KEY = os.environ.get('DO_SPACES_KEY')
DO_SPACES_SECRET = os.environ.get('DO_SPACES_SECRET')
DO_SPACES_ENDPOINT = os.environ.get('DO_SPACES_ENDPOINT')
DO_SPACES_BUCKET = os.environ.get('DO_SPACES_BUCKET')

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
        config=Config(signature_version='s3v4')
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
        print(f"✅ Uploaded file to DO Spaces: {object_key}")
        return True
    except Exception as e:
        print(f"❌ Failed to upload to DO Spaces: {e}")
        return False

def generate_character(prompt, save_dir="./downloads", output_format="jpg", client_webhook_url=None):
    """
    Generate a character using the API and print job details.
    """
    try:
        # !!! REPLACE THIS WITH YOUR ACTUAL LISTENER URL if using client webhook !!!
        # If you don't need client-side callbacks for *this specific script*,
        # you can omit client_webhook_url or set it to None.
        # The server will still use its internal webhook for Replicate.
        
        # Updated endpoint for new modular structure
        endpoint = "/api/image-generation/generate/"
        url = BASE_URL + endpoint
        
        payload = {
            "prompt": prompt,
        }
        
        # Only include client_webhook_url if it's provided
        if client_webhook_url:
            payload["client_webhook_url"] = client_webhook_url
        
        print(f"Sending request to {url}...")
        # print(f"Prompt: {prompt}") # Will print later
        # if client_webhook_url:
        #     print(f"Client Webhook URL: {client_webhook_url}")
        
        # Send the request
        response = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
        # Extract job info
        character_id = data.get('id')
        status = data.get('status')
        replicate_prediction_id_str = data.get('replicate_prediction_id') # Get the ID string

        print("\n✅ Image generation job submitted successfully!")
        print(f"Prompt: {prompt}")
        print(f"Job ID: {character_id}")
        if replicate_prediction_id_str:
            print(f"Replicate Prediction Link: https://replicate.com/p/{replicate_prediction_id_str}")
        print(f"Initial Status: {status}")
        
        # Display client webhook URL if provided
        if client_webhook_url:
            print(f"Client Webhook URL: {client_webhook_url}")
            print("Status updates will be sent to your webhook URL when the job status changes")
        
        print("\nFull API Response:")
        print(json.dumps(data, indent=2))
        # Script will now exit after this function returns

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error generating character: {e}")
        # Print server response if available
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server Response Status Code: {e.response.status_code}")
            try:
                error_details = e.response.json()
                print(f"Server Error Details:\n{json.dumps(error_details, indent=2)}")
            except json.JSONDecodeError:
                print(f"Server Response Body:\n{e.response.text}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")


# Main execution block
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a character using the API")
    parser.add_argument("prompt", nargs="?", default="A detailed portrait of a cyberpunk samurai with neon helmet", 
                      help="The prompt for character generation")
    parser.add_argument("--webhook", type=str, help="Optional client webhook URL for status updates")
    args = parser.parse_args()
    
    # Generate character with the provided prompt and webhook URL
    generate_character(args.prompt, client_webhook_url=args.webhook)
    # Script exits after generate_character finishes