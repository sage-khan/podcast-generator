import os
import sys
import argparse
import requests
import time
from dotenv import load_dotenv
import logging
from datetime import datetime
from urllib.parse import urlparse

# Setup Django environment to use storage_client
import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_image_gen.settings')
django.setup()
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

def submit_lipsync_job(base_url, auth_header, video_url, audio_url):
    """Submits a lipsync job and returns the job ID."""
    api_url = f"{base_url}/api/videos/generate/kling/lipsync/"
    payload = {
        'video_url': video_url,
        'audio_file': audio_url
    }
    logging.info(f"Submitting lipsync job for video {video_url} and audio {audio_url}")
    try:
        response = requests.post(api_url, json=payload, headers=auth_header)
        response.raise_for_status()
        job_id = response.json().get('id')
        if not job_id:
            raise ValueError("API response did not include a job ID.")
        logging.info(f"Job submitted with ID: {job_id}")
        return job_id
    except requests.RequestException as e:
        logging.error(f"Failed to submit job: {e}")
        raise

def poll_for_video_url(base_url, auth_header, job_id):
    """Polls the status endpoint until the job is complete and returns the video URL."""
    status_url = f"{base_url}/api/videos/generate/kling/lipsync/{job_id}/"
    while True:
        try:
            response = requests.get(status_url, headers=auth_header)
            response.raise_for_status()
            data = response.json()
            status = data.get('status', '').lower()
            logging.info(f"Job {job_id} status: {status}")

            if status in ['succeeded', 'completed']:
                output_url = data.get('output', {}).get('url') or data.get('output_url')
                if not output_url:
                    raise ValueError("Job completed but no output URL found.")
                logging.info(f"Job {job_id} completed. Video URL: {output_url}")
                return output_url
            elif status in ['failed', 'error']:
                error_message = data.get('error', 'Unknown error.')
                raise RuntimeError(f"Lipsync job failed: {error_message}")
            
            time.sleep(20)
        except requests.RequestException as e:
            logging.error(f"Polling failed for job {job_id}: {e}")
            time.sleep(20)

def download_video(video_url, output_path):
    """Downloads a video from a URL."""
    try:
        logging.info(f"Downloading video from {video_url} to {output_path}")
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded video to {output_path}")
    except requests.RequestException as e:
        logging.error(f"Failed to download video: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Lipsync a video with an audio file using the Kling API.")
    parser.add_argument("--video_url", required=True, help="URL of the input video.")
    parser.add_argument("--audio_url", required=True, help="URL of the input audio.")
    parser.add_argument("--output_dir", default="./media/output/lipsync", help="Directory to save the output video.")
    parser.add_argument("--api_base_url", default=os.environ.get("API_BASE_URL", "http://localhost:8000"), help="Base URL of the API.")
    parser.add_argument("--username", default=os.environ.get("API_USERNAME"), help="Username for API authentication.")
    parser.add_argument("--password", default=os.environ.get("API_PASSWORD"), help="Password for API authentication.")

    args = parser.parse_args()

    if not args.username or not args.password:
        logging.error("API username and password are required.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    video_url = args.video_url
    if video_url and 'digitaloceanspaces.com' in video_url:
        video_url = storage_client.get_accessible_url(video_url)
        logging.info(f"Converted video URL to public: {video_url}")

    audio_url = args.audio_url
    if audio_url and 'digitaloceanspaces.com' in audio_url:
        audio_url = storage_client.get_accessible_url(audio_url)
        logging.info(f"Converted audio URL to public: {audio_url}")

    try:
        token, token_type = get_auth_token(args.api_base_url, args.username, args.password)
        auth_header = {'Authorization': f'{token_type} {token}', 'Content-Type': 'application/json'}

        job_id = submit_lipsync_job(args.api_base_url, auth_header, video_url, audio_url)
        video_url = poll_for_video_url(args.api_base_url, auth_header, job_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.basename(urlparse(args.video_url).path)
        audio_filename = os.path.basename(urlparse(args.audio_url).path)
        video_name_part = os.path.splitext(video_filename)[0]
        audio_name_part = os.path.splitext(audio_filename)[0]
        output_filename = f"lipsync_{video_name_part}_{audio_name_part}_{timestamp}.mp4"
        output_path = os.path.join(args.output_dir, output_filename)

        download_video(video_url, output_path)
        logging.info(f"Video downloaded and saved to {output_path}")

        print(f"Video saved to: {output_path}")

    except (ValueError, RuntimeError, requests.RequestException) as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
