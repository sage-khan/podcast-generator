import os
import sys
import argparse
import requests
import time
from dotenv import load_dotenv
import logging
from datetime import datetime
import json
from urllib.parse import urljoin

# Setup storage_client import path (no Django required)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.clients.storage_client import storage_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def get_auth_token(base_url, username, password):
    """Get authentication token from API."""
    auth_url = f"{base_url}/api/token/"
    try:
        response = requests.post(auth_url, data={'username': username, 'password': password})
        response.raise_for_status()
        data = response.json()
        return (data.get('access'), 'Bearer') if 'access' in data else (data.get('token'), 'Token')
    except requests.RequestException as e:
        logging.error(f"Authentication failed: {e}")
        raise

def start_image_job(base_url, auth_header, subject_image_url, background_image_url, prompt, aspect_ratio, seed, output_format, safety_tolerance):
    """
    Submits a job to the appropriate image editing API endpoint.
    """
    if background_image_url:
        # Use the multi-image-list endpoint when both subject and background are provided
        endpoint = '/api/images/generate/flux/kontext/multi-image-list/'
        payload = {
            'input_images': [subject_image_url, background_image_url],
            'prompt': prompt,
            'aspect_ratio': aspect_ratio,
            'output_format': output_format,
            'safety_tolerance': safety_tolerance
        }
        status_endpoint = '/api/images/generate/flux/kontext/multi-image-list/'
    else:
        endpoint = '/api/images/generate/flux/kontext/pro/'
        payload = {
            'input_image': subject_image_url,
            'prompt': prompt,
            'aspect_ratio': aspect_ratio,
            'output_format': output_format,
            'safety_tolerance': safety_tolerance
        }
        status_endpoint = '/api/images/generate/flux/kontext/pro/'

    if seed is not None:
        payload['seed'] = seed

    url = urljoin(base_url, endpoint)
    try:
        response = requests.post(url, json=payload, headers=auth_header)
        response.raise_for_status()
        job_id = response.json().get('id')
        if not job_id:
            raise ValueError("API response did not include a job ID.")
        logging.info(f"Job submitted with ID: {job_id}")
        return job_id, status_endpoint
    except requests.RequestException as e:
        logging.error(f"Failed to submit job: {e}")
        raise

def poll_for_image_url(base_url, auth_header, job_id, endpoint):
    """Polls the status endpoint until the job is complete and returns the image URL."""
    status_url = f"{base_url}{endpoint}{job_id}/"
    while True:
        try:
            response = requests.get(status_url, headers=auth_header)
            response.raise_for_status()
            data = response.json()
            status = data.get('status', '').lower()
            logging.info(f"Job {job_id} status: {status}")

            if status in ['succeeded', 'completed']:
                # The API may return different keys depending on endpoint version
                image_url = None
                if isinstance(data.get('output'), list):
                    image_url = data['output'][0]
                elif data.get('output_url'):
                    image_url = data['output_url']
                elif isinstance(data.get('output_urls'), list):
                    image_url = data['output_urls'][0]

                if not image_url:
                    raise ValueError("Job completed but no output URL found.")

                logging.info(f"Job {job_id} completed. Image URL: {image_url}")
                return image_url
            elif status in ['failed', 'error']:
                error_message = data.get('error', 'Unknown error.')
                raise RuntimeError(f"Image generation failed: {error_message}")
            
            time.sleep(10)
        except requests.RequestException as e:
            logging.error(f"Polling failed for job {job_id}: {e}")
            time.sleep(10)

def download_image(image_url, output_path):
    """Downloads an image from a URL."""
    try:
        logging.info(f"Downloading image from {image_url} to {output_path}")
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded image to {output_path}")
    except requests.RequestException as e:
        logging.error(f"Failed to download image: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Edit an image using Flux Kontext APIs.")
    parser.add_argument("--subject_image_url", required=True, help="URL of the subject image.")
    parser.add_argument("--background_image_url", help="URL of the background image. If omitted, the image will be edited in place using Kontext Pro.")
    parser.add_argument("--prompt", required=True, help="Prompt describing how to combine or transform the images.")
    parser.add_argument("--aspect_ratio", default="match_input_image", help="Aspect ratio of the output image. Use 'match_input_image' to keep the same AR as the subject image.")
    parser.add_argument("--seed", type=int, help="Optional random seed for reproducibility.")
    parser.add_argument("--output_format", default="png", choices=["png", "jpg", "jpeg", "webp"], help="Output format for the generated image.")
    parser.add_argument("--safety_tolerance", type=int, default=2, choices=[0,1,2], help="Safety tolerance (0=strict, 2=permissive).")
    parser.add_argument("--output_dir", default="./media/output/images", help="Directory to save the output image.")
    parser.add_argument("--api_base_url", default=os.environ.get("API_BASE_URL", "http://localhost:8000"), help="Base URL of the API.")
    parser.add_argument("--username", default=os.environ.get("API_USERNAME"), help="Username for API authentication.")
    parser.add_argument("--password", default=os.environ.get("API_PASSWORD"), help="Password for API authentication.")

    args = parser.parse_args()

    if not args.username or not args.password:
        logging.error("API username and password are required.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    subject_image_url = args.subject_image_url
    if subject_image_url and 'digitaloceanspaces.com' in subject_image_url:
        subject_image_url = storage_client.get_accessible_url(subject_image_url)
        logging.info(f"Converted subject image URL to public: {subject_image_url}")

    background_image_url = args.background_image_url
    if background_image_url and 'digitaloceanspaces.com' in background_image_url:
        background_image_url = storage_client.get_accessible_url(background_image_url)
        logging.info(f"Converted background image URL to public: {background_image_url}")

    try:
        token, token_type = get_auth_token(args.api_base_url, args.username, args.password)
        auth_header = {'Authorization': f'{token_type} {token}', 'Content-Type': 'application/json'}

        job_id, status_endpoint = start_image_job(
            args.api_base_url,
            auth_header,
            subject_image_url,
            background_image_url,
            args.prompt,
            args.aspect_ratio,
            args.seed,
            args.output_format,
            args.safety_tolerance
        )

        image_url = poll_for_image_url(args.api_base_url, auth_header, job_id, status_endpoint)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_prompt = "".join(c for c in args.prompt if c.isalnum() or c in (' ', '_')).rstrip()
        sanitized_prompt = sanitized_prompt.replace(' ', '_')[:50]
        file_extension = os.path.splitext(image_url.split('?')[0])[-1] or '.png'
        output_filename = os.path.join(args.output_dir, f"edited_image_{sanitized_prompt}_{timestamp}{file_extension}")

        download_image(image_url, output_filename)

        print(f"Image saved to: {output_filename}")

    except (ValueError, RuntimeError, requests.RequestException) as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
