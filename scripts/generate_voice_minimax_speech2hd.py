import os
import sys
import json
import argparse
import requests
import time
from dotenv import load_dotenv
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def _ensure_scheme(url: str) -> str:
    """Ensure the URL starts with http:// or https://.

    Default behaviour:
      • For localhost / 127.* hosts we default to plain HTTP as most dev servers are un-encrypted.
      • All other hosts default to HTTPS for safety.
    """
    if url.startswith(('http://', 'https://')):
        return url

    host = url.split('/')[0]  # up to first slash if present
    if host.startswith('localhost') or host.startswith('127.'):
        return f"http://{url.lstrip('/')}"
    return f"https://{url.lstrip('/')}"

def get_auth_token(base_url, username, password):
    """Get authentication token from API."""
    auth_url = f"{base_url}/api/token/"
    try:
        response = requests.post(auth_url, data={'username': username, 'password': password})
        response.raise_for_status()
        response_json = response.json()
        if 'access' in response_json:
            return response_json['access'], 'Bearer'
        elif 'token' in response_json:
            return response_json['token'], 'Token'
        else:
            raise ValueError(f"Unknown token format in response: {response_json}")
    except requests.RequestException as e:
        logging.error(f"Authentication failed: {e}")
        raise

def submit_tts_job(base_url, auth_header, text, voice_id, model, language="en"):
    """Submits a text-to-speech job and returns the job ID."""
    # Note: The endpoint URL is constructed based on the selected model.
    # This assumes a URL structure like /api/audio/generate/minimax/<model-name>/
    api_url = f"{base_url}/api/audio/generate/minimax/{model}/"
    payload = {
        'text': text,
        'voice_id': voice_id,
        'language': language,
    }
    logging.info(f"Submitting TTS job with model {model} for voice {voice_id}")
    try:
        response = requests.post(api_url, json=payload, headers=auth_header)
        response.raise_for_status()
        resp_json = response.json()
        job_id = resp_json.get('id') or resp_json.get('job_id')
        if not job_id:
            raise ValueError(f"API response did not include a job ID. Full response: {resp_json}")
        logging.info(f"TTS job submitted with ID: {job_id}")
        return job_id
    except requests.RequestException as e:
        logging.error(f"Failed to submit TTS job: {e}")
        raise

def poll_for_audio_url(base_url, auth_header, job_id, model, poll_interval=10, max_wait=600):
    """Polls the status endpoint until the job is complete and returns the audio URL."""
    status_url = f"{base_url}/api/audio/generate/minimax/{model}/{job_id}/"
    start_time = time.time()
    while True:
        try:
            response = requests.get(status_url, headers=auth_header)
            response.raise_for_status()
            data = response.json()
            status = data.get('status', '').lower()

            logging.info(f"Job {job_id} status: {status}")

            if status == 'succeeded' or status == 'completed':
                # Different deployments may return the final audio URL in various fields. Try them in order.
                audio_url = (
                    data.get('output', {}).get('audio_url')
                    or data.get('audio_url')
                    or data.get('output')             # Some APIs put the direct URL in 'output'
                    or data.get('output_url')         # Our backend uses this field
                )
                if not audio_url:
                    logging.error(f"Job completed but no audio URL found in response: {data}")
                    raise ValueError("Could not extract audio URL from completed job.")
                logging.info(f"Job {job_id} completed. Audio URL: {audio_url}")
                return audio_url
            
            elif status in ['failed', 'error']:
                error_message = data.get('error', 'Unknown error.')
                logging.error(f"Job {job_id} failed: {error_message}")
                raise RuntimeError(f"TTS generation failed: {error_message}")

            # Timeout check
            if (time.time() - start_time) > max_wait:
                raise TimeoutError(f"Polling exceeded max_wait={max_wait}s for job {job_id}")

            time.sleep(poll_interval)

        except requests.RequestException as e:
            logging.error(f"Polling failed for job {job_id}: {e}")
            time.sleep(poll_interval)

def download_audio_file(audio_url, output_path):
    """Downloads the audio file from a URL."""
    try:
        logging.info(f"Downloading audio from {audio_url} to {output_path}")
        response = requests.get(audio_url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded audio to {output_path}")
    except requests.RequestException as e:
        logging.error(f"Failed to download audio file: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Generate speech from text using the the podcast-generator API.")
    parser.add_argument("--text", required=True, help="The text to convert to speech.")
    parser.add_argument("--voice_id", required=True, help="The voice ID of the speaker.")
    parser.add_argument("--speaker_name", required=True, help="The name of the speaker for file naming.")
    parser.add_argument("--model", default="speech-02-hd", choices=["speech-02-hd", "speech-02-HD", "speech-02-turbo"], help="The TTS model to use.")
    parser.add_argument("--language", default="en", help="Language code for speech synthesis (e.g., 'en', 'zh').")
    parser.add_argument("--output_dir", default="./media/output/audio", help="Directory to save the output audio file.")
    parser.add_argument("--api_base_url", default=os.environ.get("API_BASE_URL", "localhost:8000"), help="Base URL of the API (with or without scheme).")
    parser.add_argument("--username", default=os.environ.get("API_USERNAME"), help="Username for API authentication.")
    parser.add_argument("--password", default=os.environ.get("API_PASSWORD"), help="Password for API authentication.")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between status checks.")
    parser.add_argument("--max-wait", type=int, default=600, help="Maximum seconds to wait for job completion before aborting.")

    args = parser.parse_args()

    if not args.username or not args.password:
        logging.error("API username and password are required.")
        sys.exit(1)

    # Sanitize base URL
    api_base = _ensure_scheme(args.api_base_url.rstrip('/'))

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    try:
        token, token_type = get_auth_token(api_base, args.username, args.password)
        auth_header = {'Authorization': f'{token_type} {token}', 'Content-Type': 'application/json'}

        job_id = submit_tts_job(api_base, auth_header, args.text, args.voice_id, args.model.lower(), language=args.language)
        audio_url = poll_for_audio_url(api_base, auth_header, job_id, args.model.lower(), poll_interval=args.poll_interval, max_wait=args.max_wait)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(audio_url.split('?')[0])[-1]
        file_extension = ext if ext else '.wav'
        safe_speaker = args.speaker_name.replace(' ', '_')
        output_path = Path(args.output_dir) / f"{safe_speaker}-{args.voice_id}-{timestamp}{file_extension}"

        download_audio_file(audio_url, str(output_path))

        print(json.dumps({"audio_file": str(output_path)}, indent=2))

    except (ValueError, RuntimeError, requests.RequestException, TimeoutError) as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
