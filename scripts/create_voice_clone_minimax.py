#!/usr/bin/env python3
"""
Test script to verify the audio_generation API endpoints are working correctly.
"""
import os
import sys
import json
import argparse
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def normalize_base_url(base_url):
    """Return base_url with https:// if missing and without trailing slash."""
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return base_url.rstrip("/")

def get_auth_token(base_url, username, password):
    """Get authentication token from API and return (token, token_type)."""
    auth_url = f"{base_url}/api/token/"
    
    try:
        response = requests.post(
            auth_url,
            data={'username': username, 'password': password}
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.text}")
        
        # Handle different token formats
        response_json = response.json()
        
        # JWT token format has 'access' key
        if 'access' in response_json:
            return response_json['access'], 'Bearer'
        # Simple token authentication format has 'token' key
        elif 'token' in response_json:
            return response_json['token'], 'Token'
        else:
            raise Exception(f"Unknown token format in response: {response_json}")
            
    except requests.RequestException as e:
        raise Exception(f"Failed to connect to {auth_url}: {str(e)}")

def test_voice_clone_api(base_url, token, token_type, voice_file_url=None):
    """Submit a voice clone job. Returns job_id on success, else None."""
    api_url = f"{base_url}/api/audio/generate/minimax/voice-clone/"
    
    if not voice_file_url:
        voice_file_url = "https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/audio/R8_WQTHN3AP.wav"
    
    # Prepare the request payload
    payload = {
        'voice_file': voice_file_url,
        'model': 'speech-02-hd',
        'accuracy': 0.7,
        'need_noise_reduction': True,
        'need_volume_normalization': True
    }
    
    # Set up the authorization header
    headers = {
        'Authorization': f'{token_type} {token}',
        'Content-Type': 'application/json'
    }
    
    print(f"Testing voice clone API: {api_url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Make the API request
        response = requests.post(api_url, json=payload, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 201 and response.status_code != 202:
            print(f"API request failed: {response.text}")
            return None
        
        response_data = response.json()
        print(f"Response data: {json.dumps(response_data, indent=2)}")
        
        job_id = response_data.get('id')
        if job_id:
            print(f"\nVoice clone job created with ID: {job_id}")
            print(f"Check status with: {base_url}/api/audio/generate/minimax/voice-clone/{job_id}/")
            return job_id
        return None
        
    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None

def test_voice_clone_status(base_url, token, token_type, job_id):
    """Fetch job status once; returns JSON dict or None."""
    api_url = f"{base_url}/api/audio/generate/minimax/voice-clone/{job_id}/"
    
    # Set up the authorization header
    headers = {'Authorization': f'{token_type} {token}'}
    
    print(f"Testing voice clone status API: {api_url}")
    
    try:
        # Make the API request
        response = requests.get(api_url, headers=headers)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"API request failed: {response.text}")
            return None
        
        response_data = response.json()
        print(f"Response data: {json.dumps(response_data, indent=2)}")
        
        return response_data
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

def save_json(data, output_dir, filename):
    """Save dict `data` to `output_dir/filename`. Creates directory."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {filename} to {path}")

def save_status_json(data, output_dir, job_id):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_json(data, output_dir, f"voice_clone_status_{job_id}_{ts}.json")

def fetch_replicate_prediction(prediction_url, replicate_token):
    """Fetch prediction JSON from Replicate API."""
    if not replicate_token:
        print("Replicate token not provided; skipping replicate fetch.")
        return None
    headers = {"Authorization": f"Bearer {replicate_token}"}
    try:
        resp = requests.get(prediction_url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Failed to fetch replicate prediction: {e}")
        return None

def poll_voice_clone_status(base_url, token, token_type, job_id, interval, output_dir, replicate_token):
    """Poll status endpoint until terminal state; saves JSONs and returns final data."""
    terminal_status = {"completed", "succeeded", "failed"}
    while True:
        data = test_voice_clone_status(base_url, token, token_type, job_id)
        if not data:
            print("Failed to fetch status JSON, retrying...")
            time.sleep(interval)
            continue
        status = data.get("status", "").lower()
        voice_id = data.get("voice_id")
        if status in terminal_status or voice_id:
            save_status_json(data, output_dir, job_id)
            # If replicate_url present, fetch replicate JSON
            replicate_url = data.get("replicate_url")
            if replicate_url:
                rep_json = fetch_replicate_prediction(replicate_url, replicate_token)
                if rep_json:
                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    save_json(rep_json, output_dir, f"replicate_prediction_{job_id}_{ts}.json")
            return data
        print(f"Current status: {status or 'unknown'} (voice_id: {voice_id}); polling again in {interval}s ...")
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description='Test audio_generation API endpoints')
    parser.add_argument('--base-url', default='example.com', help='Base URL of the API (with or without scheme)')
    parser.add_argument('--username', required=True, help='Username for API authentication')
    parser.add_argument('--password', required=True, help='Password for API authentication')
    parser.add_argument('--voice-file', help='URL to voice file for cloning')
    parser.add_argument('--audio-path', dest='voice_file_alt', help='Alias for --voice-file (deprecated)')
    parser.add_argument('--speaker-name', help='Optional speaker name for metadata')
    parser.add_argument('--job-id', help='Job ID to check status (if not provided, will create a new job)')
    parser.add_argument('--only-status', action='store_true', help='Only check job status, don\'t create a new job')
    parser.add_argument('--output-dir', default='./media/voice_clone_status', help='Directory to save JSON outputs')
    parser.add_argument('--poll-interval', type=int, default=15, help='Seconds between status polls')
    parser.add_argument('--replicate-token', help='Replicate API token (or set REPLICATE_API_TOKEN env)')
    parser.add_argument('--base-filename', help='Base filename (without extension or voice_id) for the final combined JSON. If provided, a single JSON <base_filename>-<voice_id>.json will be written.')
    
    args = parser.parse_args()
    
    try:
        # Normalise base URL to include scheme and no trailing slash
        args.base_url = normalize_base_url(args.base_url)
        
        print(f"Testing API at {args.base_url}")
        
        # Get authentication token
        print("Authenticating with API...")
        token, token_type = get_auth_token(args.base_url, args.username, args.password)
        print("Authentication successful!")
        
        # Replicate token
        replicate_token = args.replicate_token or os.getenv("REPLICATE_API_TOKEN")
        
        # Determine voice file URL (support deprecated alias)
        if not args.voice_file and args.voice_file_alt:
            args.voice_file = args.voice_file_alt
        
        job_id = args.job_id
        
        # Submit job if not only-status mode
        if not args.only_status:
            print("\nSubmitting voice clone job...")
            job_id = test_voice_clone_api(args.base_url, token, token_type, args.voice_file)
            print("Voice clone submission:", "PASSED" if job_id else "FAILED")
        
        if job_id:
            # Poll until completion and save outputs
            final_data = poll_voice_clone_status(
                args.base_url,
                token,
                token_type,
                job_id,
                interval=args.poll_interval,
                output_dir=args.output_dir,
                replicate_token=replicate_token,
            )
            
            # If base_filename specified, save combined JSON and print path
            if args.base_filename and final_data:
                voice_id = final_data.get('voice_id')
                combined = {
                    'server_status': final_data,
                    'speaker_name': args.speaker_name,
                }
                fname_vo = f"{args.base_filename}-{voice_id}.json" if voice_id else f"{args.base_filename}.json"
                json_path = os.path.join(args.output_dir, fname_vo)
                save_json(combined, args.output_dir, fname_vo)
                # Print machine-readable output
                print(json.dumps({"voice_id": voice_id, "json_path": json_path}))
             
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
