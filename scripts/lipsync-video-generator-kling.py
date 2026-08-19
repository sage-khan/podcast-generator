#!/usr/bin/env python3
"""
Test the Kling lipsync API endpoint by applying audio to a video.

Usage:
  python scripts/test_lipsync.py \
      --video-url https://replicate.delivery/xezq/e1Uxjn4DLL2yRiLiqpW0UrfBouSWpVbfA2czxOAG2zH9CkzpA/tmpcfumloqd.mp4 \
      --audio-file-url https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/audio/R8_WQTHN3AP.wav \
      --api-base https://example.com \
      --username admin --password admin1234 \
      --output-path ./media/lipsync/output.mp4

You can also use a local audio file:
  python scripts/test_lipsync.py \
      --video-url https://replicate.delivery/xezq/e1Uxjn4DLL2yRiLiqpW0UrfBouSWpVbfA2czxOAG2zH9CkzpA/tmpcfumloqd.mp4 \
      --audio-file ./path/to/audio.mp3 \
      --api-base https://example.com \
      --username admin --password admin1234 \
      --output-path ./media/lipsync/output.mp4

Input Parameters:
  --video-url      : URL to the video to apply lipsync to (required)
  --audio-file-url : URL to the audio file to use for lipsync (optional)
  --audio-file     : Path to local audio file to upload (alternative to audio-file-url)
  --api-base       : API endpoint (default: https://example.com) 
  --username       : API username (default: from env DJANGO_SUPERUSER_USERNAME)
  --password       : API password (default: from env DJANGO_SUPERUSER_PASSWORD)
  --output-path    : Local path to save the output video (optional)
  --max-polls      : Maximum number of polling attempts (default: 60)
  --poll-interval  : Seconds between polling attempts (default: 10)

Output:
  1. URL of the generated lipsync video
  2. Path to downloaded video file (if --output-path is specified)


lipsync URLS: (10s) https://replicate.delivery/xezq/0IKCKHiqPHaLFlOnSEFGX7TPPQB33oxbLShioed2oOl1VBdKA/tmp4ix5quta.mp4

(5s) https://replicate.delivery/xezq/k1LFHIlHeLQxIKePtgePFvn4OemuRoFjqfkPuXyXpQ5GbfhOF/tmpy49slwj8.mp4

"""

# Load environment variables first, before any imports
import os
import sys
from dotenv import load_dotenv

# Try to load credentials from multiple possible .env files
load_dotenv()  # Default .env file
load_dotenv('.env-do')  # DO-specific env vars
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))  # Project root .env

import argparse
import time
import json
import requests
import tempfile
from pathlib import Path
from pprint import pprint
from urllib.parse import urlparse
import logging
import re
import uuid
import boto3
from time import time as get_timestamp
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('lipsync_test')

def get_token(base, user, pwd):
    """Return (scheme, token_str) for Authorization header."""
    print(f"Authenticating with username: {user}")
    r = requests.post(
        f"{base}/api/token/",
        data={"username": user, "password": pwd},
        timeout=30,
    )
    
    print(f"Auth response: {r.status_code}")
    print(r.text)
    
    r.raise_for_status()
    data = r.json()
    
    if "access" in data:  # SimpleJWT style
        return "Bearer", data["access"]
    if "token" in data:   # DRF TokenAuthentication style
        return "Token", data["token"]
    
    raise ValueError(f"Unexpected token format: {data}")

def upload_file(file_path, base, headers):
    """Upload a file to the API's file upload endpoint.

    Falls back to storage_client (DigitalOcean Spaces) if the API does not
    expose /api/uploads/ (returns 404)."""
    print(f"Uploading file via API: {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            r = requests.post(
                f"{base}/api/uploads/",
                headers={k: v for k, v in headers.items() if k != 'Content-Type'},
                files=files,
                timeout=60
            )
            if r.status_code == 404:
                raise requests.HTTPError("/api/uploads/ not found", response=r)
            r.raise_for_status()
            url = r.json().get('url')
            if not url:
                raise ValueError("No 'url' field in upload response")
            print(f"API upload succeeded, URL: {url}")
            return url
    except requests.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            print("/api/uploads/ endpoint missing; falling back to storage_client upload …")
        else:
            print(f"HTTP error uploading file: {http_err}; falling back to storage_client …")
    except Exception as e:
        print(f"General error uploading via API: {e}; falling back to storage_client …")

    # Fallback → storage_client (DigitalOcean Spaces or local)
    try:
        if storage_client:
            uploaded_url = storage_client.upload_file(file_path, endpoint_type='video_generation')
            if uploaded_url:
                print(f"storage_client upload succeeded, URL: {uploaded_url}")
                return uploaded_url
            else:
                print("storage_client.upload_file returned None – will try tmpfiles.io …")
    except Exception as e:
        print(f"storage_client upload failed: {e}")

    # Last-chance fallback: tmpfiles.io
    try:
        import requests as _r
        with open(file_path, 'rb') as f:
            resp = _r.post('https://tmpfiles.org/api/v1/upload', files={'file': f}, timeout=60)
            resp.raise_for_status()
            tmp_url = resp.json().get('data', {}).get('url')
            if tmp_url:
                print(f"Uploaded to tmpfiles.io → {tmp_url}")
                return tmp_url
    except Exception as e:
        print(f"tmpfiles.io fallback failed: {e}")

    raise RuntimeError("Failed to upload audio file via all mechanisms")

# Create a boto3 S3 client for DO Spaces
try:
    # First check if the required credentials are available
    do_key = os.environ.get('DO_SPACES_KEY')
    do_secret = os.environ.get('DO_SPACES_SECRET')
    do_region = os.environ.get('DO_SPACES_REGION', 'nyc3')
    do_endpoint = os.environ.get('DO_SPACES_ENDPOINT', f'https://{do_region}.digitaloceanspaces.com')
    
    if not do_key or not do_secret:
        print("Warning: DO_SPACES_KEY or DO_SPACES_SECRET environment variables are not set")
        s3_client = None
    else:
        print(f"Creating S3 client with region={do_region}, endpoint={do_endpoint}")
        s3_client = boto3.client(
            's3',
            region_name=do_region,
            endpoint_url=do_endpoint,
            aws_access_key_id=do_key,
            aws_secret_access_key=do_secret
        )
        print("Successfully created S3 client for DO Spaces")
except Exception as e:
    print(f"Error creating S3 client: {e}")
    s3_client = None

# Import the storage client from the project for non-DO operations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.clients.storage_client import storage_client
    print("Storage client imported successfully")
except ImportError:
    print("Could not import storage_client")
    storage_client = None

def prepare_accessible_audio(url, local_storage_path=None):
    """Make the input audio accessible to external APIs.
    
    If local_storage_path is provided and BASE_MEDIA_URL is set in environment:
    - Downloads the audio to local_storage_path
    - Constructs a URL using BASE_MEDIA_URL + relative path
    
    Otherwise:
    - Downloads the audio from DO Spaces using direct credentials
    - Uploads it to a public file sharing service
    - Has multiple fallback mechanisms
    """
    try:
        print(f"Preparing audio from {url} for external API access...")
        
        # First check if the URL might already be publicly accessible
        try:
            print("Checking if URL is already publicly accessible...")
            head_response = requests.head(url, timeout=5)
            if head_response.status_code == 200:
                print("URL appears to be publicly accessible!")
                # Still do quick verification with a tiny range request
                range_headers = {'Range': 'bytes=0-1000'}
                range_response = requests.get(url, headers=range_headers, timeout=5)
                if range_response.status_code in [200, 206] and len(range_response.content) > 0:
                    print("Confirmed URL is publicly accessible - using as is")
                    return url
                else:
                    print(f"URL returned status {range_response.status_code} on range request - not publicly accessible")
            else:
                print(f"URL returned status {head_response.status_code} - not publicly accessible")
        except Exception as e:
            print(f"Error checking URL accessibility: {e}")
            
        # Create a filename from the URL
        filename = os.path.basename(urlparse(url).path) or f"audio_{uuid.uuid4().hex[:8]}.wav"
        
        # Use local storage if provided and create directory if needed
        if local_storage_path:
            if not os.path.exists(local_storage_path):
                os.makedirs(local_storage_path, exist_ok=True)
                print(f"Created local storage directory: {local_storage_path}")
            local_path = os.path.join(local_storage_path, filename)
        else:
            # Create temporary directory for downloaded audio
            temp_dir = tempfile.mkdtemp()
            local_path = os.path.join(temp_dir, filename)
        
        download_success = False
        
        # Extract bucket and key from the URL
        bucket, key = extract_bucket_and_key(url)
        if bucket and key:
            print(f"URL recognized as DO Spaces: bucket={bucket}, key={key}")
            
            if s3_client:
                try:
                    print(f"Downloading from DO Spaces using boto3: bucket={bucket}, key={key}")
                    s3_client.download_file(
                        Bucket=bucket,
                        Key=key,
                        Filename=local_path
                    )
                    
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        print(f"Download successful! ({os.path.getsize(local_path)} bytes)")
                        download_success = True
                    else:
                        print("Download reported success but file is missing or empty")
                except Exception as e:
                    print(f"Error downloading with boto3: {str(e)}")
                    
                    try:
                        print("Trying with presigned URL...")
                        presigned_url = s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': bucket, 'Key': key},
                            ExpiresIn=3600
                        )
                        print(f"Generated presigned URL: {presigned_url[:100]}...")
                        
                        response = requests.get(presigned_url, timeout=30)
                        response.raise_for_status()
                        
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        
                        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                            print(f"Presigned URL download successful! ({os.path.getsize(local_path)} bytes)")
                            download_success = True
                    except Exception as e2:
                        print(f"Presigned URL download failed: {e2}")
        
        # Try using storage_client if available
        if not download_success and storage_client:
            try:
                print("Trying to download using storage_client...")
                storage_client.download_file(url, local_path)
                
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    print(f"Storage client download successful! ({os.path.getsize(local_path)} bytes)")
                    download_success = True
                    
                    # Also try to get an accessible URL through storage_client
                    try:
                        accessible_url = storage_client.get_accessible_url(url)
                        if accessible_url and accessible_url != url:
                            print(f"Storage client provided accessible URL: {accessible_url[:100]}...")
                            # Verify the accessible URL works
                            head_resp = requests.head(accessible_url, timeout=5)
                            if head_resp.status_code == 200:
                                print("Storage client accessible URL verified working!")
                                public_url = accessible_url
                                return public_url
                    except Exception as e:
                        print(f"Could not get accessible URL via storage_client: {e}")
            except Exception as e:
                print(f"Storage client download failed: {e}")
        
        # Try direct HTTP request as fallback
        if not download_success:
            try:
                print("Falling back to direct HTTP request...")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    print(f"Direct HTTP download successful! ({os.path.getsize(local_path)} bytes)")
                    download_success = True
            except Exception as e:
                print(f"Direct HTTP request failed: {str(e)}")
        
        if not download_success:
            raise Exception("Failed to download the audio file after multiple attempts")
        
        # If using local storage and BASE_MEDIA_URL is set, construct a URL
        public_url = None
        if local_storage_path and os.environ.get('BASE_MEDIA_URL'):
            try:
                # Get relative path from script directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)  # Assume script is in scripts/ subdir
                
                # Calculate relative path from project root to the file
                rel_path = os.path.relpath(local_path, project_root)
                
                # Construct URL using BASE_MEDIA_URL
                base_url = os.environ.get('BASE_MEDIA_URL').rstrip('/')
                public_url = f"{base_url}/{rel_path.replace(os.sep, '/')}"
                
                print(f"Local file accessible at: {public_url}")
            except Exception as e:
                print(f"Error constructing local media URL: {e}")
                public_url = None
        
        # If not using local storage or BASE_MEDIA_URL not set, use tmpfiles.io
        if not public_url:
            try:
                print("Uploading to tmpfiles.io for public access...")
                with open(local_path, 'rb') as f:
                    upload_url = "https://tmpfiles.io/api/v1/upload"
                    files = {'file': (os.path.basename(local_path), f, 'audio/wav')}
                    response = requests.post(upload_url, files=files, timeout=60)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("success", False):
                        public_url = data.get("data", {}).get("url")
                        print(f"Uploaded to tmpfiles.io: {public_url}")
                    else:
                        print(f"tmpfiles.io upload returned error: {data}")
            except Exception as e:
                print(f"tmpfiles.io upload failed: {e}")
                public_url = None

        # Fallback to transfer.sh if tmpfiles failed
        if not public_url:
            try:
                print("Uploading to transfer.sh as fallback...")
                filename = os.path.basename(local_path)
                with open(local_path, 'rb') as f:
                    response = requests.put(f"https://transfer.sh/{filename}", data=f, timeout=60)
                    response.raise_for_status()
                    # transfer.sh returns the URL in plain text
                    public_url = response.text.strip()
                    print(f"Uploaded to transfer.sh: {public_url}")
            except Exception as e:
                print(f"transfer.sh upload failed: {e}")
                public_url = None

        # Last fallback: presigned URL directly from DO Spaces (may still be inaccessible externally)
        if not public_url and s3_client and bucket and key:
            try:
                print("Generating presigned URL as last resort...")
                public_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600
                )
                print(f"Generated presigned URL: {public_url[:100]}...")
            except Exception as e:
                print(f"Failed to generate presigned URL: {e}")
                public_url = None

        if not public_url:
            raise Exception("Unable to obtain a public URL for the audio after multiple attempts")

        print(f"Audio available at public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error preparing accessible audio: {str(e)}")
        
        # LAST RESORT: If all else fails, try to use the original URL
        print("\n*** WARNING: All attempts to make audio accessible failed ***")
        print("Attempting to submit job with original URL as last resort.")
        print("This may work if the URL is already accessible to the lipsync service.")
        print(f"Original URL: {url}")
        
        # Return the original URL as a last resort
        return url
    finally:
        # Clean up temp files only if using temporary directory
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory: {e}")

def extract_bucket_and_key(url):
    """Extract bucket name and object key from DigitalOcean Spaces URL."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path.lstrip('/')  # remove leading slash

        # Style 1 & 2: bucket in subdomain (e.g., bucket.nyc3.digitaloceanspaces.com or bucket.nyc3.cdn.digitaloceanspaces.com)
        m = re.match(r'^(?P<bucket>[A-Za-z0-9\-]+)\.nyc3(?:\.cdn)?\.digitaloceanspaces\.com$', host)
        if m:
            bucket = m.group('bucket')
            return bucket, path

        # Style 3: path style (e.g., nyc3.digitaloceanspaces.com/bucket/key)
        if host == 'nyc3.digitaloceanspaces.com':
            # first segment of path is bucket
            parts = path.split('/', 1)
            if len(parts) == 2:
                bucket, key = parts
                return bucket, key
    except Exception as e:
        print(f"Error parsing URL: {e}")
        
    return None, None

def submit_lipsync_job(base, headers, video_url, audio_file_url):
    """Submit a job to combine video and audio using the Kling lipsync API."""
    print("\nSubmitting lipsync job...")
    
    data = {
        # Django API endpoint expects these parameter names
        'video_url': video_url,
        'audio_file': audio_file_url,
    }
    
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    r = requests.post(
        f"{base}/api/video/generate/kling/lipsync/",
        headers=headers,
        json=data
    )
    
    print(f"Response status: {r.status_code}")
    
    try:
        if r.status_code >= 400:
            print(f"Error: {r.status_code} {r.reason} for url: {r.url}")
            print(f"Response content: {r.text}")
            r.raise_for_status()
            
        response = r.json()
        print(f"Response data: {json.dumps(response, indent=2)}")
        
        if 'id' not in response:
            raise ValueError(f"Expected 'id' in response, got: {response}")
        
        return response['id']
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Response content: {r.text}")
        raise

def poll_lipsync_job(base, headers, job_id, max_polls=60, poll_interval=10):
    """Poll the lipsync job until it completes or fails."""
    print(f"\nPolling lipsync job {job_id} for status...")
    
    replicate_url_printed = False
    last_job_data = None

    for i in range(max_polls):
        print(f"Poll attempt {i+1}/{max_polls}...")
        
        r = requests.get(
            f"{base}/api/video/generate/kling/lipsync/{job_id}/",
            headers=headers
        )
        
        if r.status_code == 404:
            print("Job not found, waiting for it to be created...")
            time.sleep(poll_interval)
            continue
            
        r.raise_for_status()
        
        try:
            job_data = r.json()
            last_job_data = job_data

            # Print replicate URL once it becomes available
            rep_url = job_data.get('replicate_url')
            if rep_url and not replicate_url_printed:
                print(f"Replicate dashboard: {rep_url}")
                replicate_url_printed = True
            
            # Early exit: if the API already provides an output URL (some backends
            # populate it while status is still "processing"), return immediately
            early_url = job_data.get('output_url') or job_data.get('video_output_url')
            if early_url:
                print("\nOutput URL detected before job marked 'succeeded'. Returning early …")
                print(json.dumps(job_data, indent=2))
                return job_data
            
            status = job_data.get('status')
            
            print(f"Job status: {status}")
            
            if status == 'succeeded':
                print("\nJob completed successfully!")
                print("Full job data (Replicate response):")
                print(json.dumps(job_data, indent=2))
                
                # Return entire job_data so caller can use all details
                return job_data
                
            elif status == 'failed':
                error_message = job_data.get('error_message') or job_data.get('error') or "Unknown error"
                print(f"\nJob failed with error: {error_message}")
                print(f"Full job data: {json.dumps(job_data, indent=2)}")
                # Return job_data so caller can decide next steps
                return job_data
                
            elif status in ['starting', 'pending', 'processing']:
                print(f"Job is {status}, waiting {poll_interval} seconds...")
                time.sleep(poll_interval)
                
            else:
                print(f"Unknown job status: {status}")
                print(f"Full job data: {json.dumps(job_data, indent=2)}")
                time.sleep(poll_interval)
                
        except json.JSONDecodeError:
            print(f"Failed to parse response as JSON: {r.text}")
            time.sleep(poll_interval)
    
    print(f"Maximum polling attempts ({max_polls}) reached without job completion")
    if last_job_data:
        return last_job_data
    raise TimeoutError(f"Lipsync job {job_id} polling timed out after {max_polls} attempts")

def download_file(url, output_path):
    """Download a file from the given URL to the specified path."""
    print(f"\nDownloading file from {url} to {output_path}...")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    r = requests.get(url, stream=True)
    r.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"File downloaded to {output_path}")
    return output_path

def check_environment_variables():
    """Check and display status of important environment variables."""
    print("\nEnvironment Variable Status:")
    
    # Check DO Spaces variables
    do_vars = {
        'DO_SPACES_KEY': os.environ.get('DO_SPACES_KEY'),
        'DO_SPACES_SECRET': os.environ.get('DO_SPACES_SECRET'),
        'DO_SPACES_REGION': os.environ.get('DO_SPACES_REGION'),
        'DO_SPACES_ENDPOINT': os.environ.get('DO_SPACES_ENDPOINT'),
        'DO_SPACES_BUCKET': os.environ.get('DO_SPACES_BUCKET'),
        'BASE_MEDIA_URL': os.environ.get('BASE_MEDIA_URL')
    }
    
    for var, value in do_vars.items():
        if value:
            masked_value = value
            if 'SECRET' in var or 'KEY' in var:
                # Mask secrets but show first/last few chars
                if len(value) > 8:
                    masked_value = f"{value[:3]}...{value[-3:]}"
                else:
                    masked_value = "******"
            print(f"  {var}: {masked_value}")
        else:
            print(f"  {var}: [NOT SET]")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Kling lipsync API endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--video-url", required=True,
                        help="URL to the video to apply lipsync to")
    
    audio_group = parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio-file-url", 
                             help="URL to the audio file to use for lipsync")
    audio_group.add_argument("--audio-file", 
                             help="Path to local audio file to upload")
    
    parser.add_argument("--api-base", default="https://example.com",
                        help="Base URL for API calls")
    
    parser.add_argument("--username", 
                        default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"),
                        help="API username")
    
    parser.add_argument("--password",
                        default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234"),
                        help="API password")
    
    parser.add_argument("--output-path", 
                        help="Path to save the output video (optional)")
    
    parser.add_argument("--max-polls", type=int, default=60,
                        help="Maximum number of polling attempts")
    
    parser.add_argument("--poll-interval", type=int, default=10,
                        help="Seconds between polling attempts")
    
    args = parser.parse_args()
    return args

def main():
    """Run the lipsync test."""
    # Parse command line arguments
    args = parse_args()
    
    print("\n=== Kling Lipsync API Test ===")
    print(f"API Base: {args.api_base}")
    print(f"Video URL: {args.video_url}")
    
    # Check environment variables
    check_environment_variables()
    
    # Authenticate with the API
    try:
        scheme, token = get_token(args.api_base, args.username, args.password)
        hdrs = {
            "Authorization": f"{scheme} {token}",
            "Content-Type": "application/json"
        }
        print("Authentication successful!")
    except Exception as e:
        print(f"Error getting API token: {e}")
        return 1
    
    # Prepare audio URL - upload local file if provided
    original_audio_url = args.audio_file_url
    if args.audio_file:
        try:
            original_audio_url = upload_file(args.audio_file, args.api_base, hdrs)
        except Exception as e:
            print(f"Error uploading audio file: {e}")
            return 1
    
    print(f"Original audio URL: {original_audio_url}")
    
    # Make the audio URL accessible
    local_storage_path = args.output_path.rsplit('/', 1)[0] if args.output_path else None
    audio_url = prepare_accessible_audio(original_audio_url, local_storage_path)
    print(f"Using accessible audio URL: {audio_url}")
    
    # Submit lipsync job
    try:
        job_id = submit_lipsync_job(args.api_base, hdrs, args.video_url, audio_url)
        print(f"Lipsync job submitted with ID: {job_id}")
    except Exception as e:
        print(f"Error submitting lipsync job: {e}")
        return 1
    
    # Poll for job completion
    job_data = poll_lipsync_job(
        args.api_base, 
        hdrs, 
        job_id,
        max_polls=args.max_polls,
        poll_interval=args.poll_interval,
    )

    status = job_data.get('status')
    output_url = job_data.get('output_url') or job_data.get('video_output_url')

    if status == 'succeeded' and output_url:
        print(f"\nLipsync video generated! URL: {output_url}")
    else:
        print(f"\nJob finished with status: {status}")
        if output_url:
            print(f"Partial/early output URL: {output_url}")
        else:
            print("No output URL available.")
    
    # Download the output file if requested
    if args.output_path:
        try:
            downloaded_path = download_file(output_url, args.output_path)
            print(f"\nDownloaded lipsync video to: {downloaded_path}")
        except Exception as e:
            print(f"Error downloading output file: {e}")
            print(f"You can still access the file at: {output_url}")
    
    # Save output info and full job JSON to disk
    status_filename = f"lipsync_status_{job_id}.json"
    with open(status_filename, "w") as f:
        json.dump(job_data, f, indent=2)
    print(f"\nFull Replicate job JSON saved to {status_filename}")
    
    output_info = {
        "job_id": job_id,
        "video_url": args.video_url,
        "audio_file": audio_url,
        "lipsync_url": output_url,
        "local_path": args.output_path if args.output_path else None,
        "status_json": status_filename
    }
    
    with open("lipsync_output.json", "w") as f:
        json.dump(output_info, f, indent=2)
    print("\nSummary information saved to lipsync_output.json")
    
    print("\nLipsync test completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())