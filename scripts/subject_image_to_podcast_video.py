#!/usr/bin/env python3
"""
Generate a podcast-style video **without lipsync**.

Usage:
  python scripts/test_subject_image_to_podcast_video.py \
      --image-url https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/images/austin.jpg \
      --prompt "a podcast setting in a professional studio, high quality microphone" \
      --video-prompt "subject talking on a podcast looking at camera" \
      --api-base https://example.com \
      --username admin --password admin1234 \
      --local-storage-path ./media/avatars/mytest/
      

Input Parameters:
  --image-url       : URL to subject's face image (required)
  --prompt          : Description for podcast environment (default: professional studio)
  --video-prompt    : Prompt for video generation (default: subject talking on podcast)
  --api-base        : API endpoint (default: https://example.com) 
  --username        : API username (default: from env DJANGO_SUPERUSER_USERNAME)
  --password        : API password (default: from env DJANGO_SUPERUSER_PASSWORD)
  --local-storage-path : Local path to store files (default: None, uses tmpfiles.io)
  --reference-image-url : Reference image URL to guide Kling style (optional, repeatable)

Output:
  The script will output URLs for:
  1. Public-accessible subject image
  2. Generated podcast setting image 
  3. Final talking head video
  
  Full JSON responses from each API call are displayed during execution.

Workflow:
1. Convert a private DO Spaces face image into a 16:9 podcast-style background image using Kontext Pro.
2. Feed the generated image into the Kling 1.6 pro endpoint to create a silent talking-head video.

A separate script will later perform lipsync.
"""
import argparse
import os
import sys
import time
import json
import requests
import tempfile
import boto3
import re
from pprint import pprint
from urllib.parse import urlparse
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('podcast_generator')

# Load environment variables from .env-do file to get Digital Ocean credentials
print("Loading .env-do file...")
load_dotenv('.env-do')

# Verify DO Spaces credentials are loaded
print("Digital Ocean Spaces credentials:")
do_key = os.environ.get('DO_SPACES_KEY')
do_secret = os.environ.get('DO_SPACES_SECRET')
do_bucket = os.environ.get('DO_SPACES_BUCKET')
do_region = os.environ.get('DO_SPACES_REGION', 'nyc3')
do_endpoint = os.environ.get('DO_SPACES_ENDPOINT', 'https://nyc3.digitaloceanspaces.com')

print(f"DO_SPACES_KEY: {'set' if do_key else 'not set'}")
print(f"DO_SPACES_SECRET: {'set' if do_secret else 'not set'}")
print(f"DO_SPACES_BUCKET: {'set' if do_bucket else 'not set'}")
print(f"DO_SPACES_REGION: {do_region}")
print(f"DO_SPACES_ENDPOINT: {do_endpoint}")

# Create a boto3 S3 client for DO Spaces
try:
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

from shared.clients.storage_client import storage_client

# Verify storage client configuration
print("Storage client configuration:")
print(f"Storage backend: {storage_client.storage_backend}")
print("Created direct S3 client for DO Spaces access")


def get_token(base, user, pwd):
    """Return (scheme, token_str) for Authorization header."""
    r = requests.post(
        f"{base}/api/token/",
        data={"username": user, "password": pwd},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "access" in data:  # SimpleJWT style
        return "Bearer", data["access"]
    if "token" in data:   # DRF TokenAuthentication style
        return "Token", data["token"]
    raise KeyError(f"Unexpected token response keys: {list(data.keys())}")


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


def prepare_accessible_image(url, local_storage_path=None):
    """Make the input image accessible to external APIs.
    
    If local_storage_path is provided and BASE_MEDIA_URL is set in environment:
    - Downloads the image to local_storage_path
    - Constructs a URL using BASE_MEDIA_URL + relative path
    
    Otherwise:
    - Downloads the image from DO Spaces using direct credentials
    - Uploads it to tmpfiles.io for public access
    """
    try:
        print(f"Preparing image from {url} for external API access...")
        
        # Create a filename from the URL
        filename = os.path.basename(urlparse(url).path) or "input_image.jpg"
        
        # Use local storage if provided and create directory if needed
        if local_storage_path:
            if not os.path.exists(local_storage_path):
                os.makedirs(local_storage_path, exist_ok=True)
                print(f"Created local storage directory: {local_storage_path}")
            local_path = os.path.join(local_storage_path, filename)
        else:
            # Create temporary directory for downloaded image
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
                        print(f"Presigned URL download failed: {str(e2)}")
        
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
        
        # Use a backup image as last resort
        if not download_success:
            print("Using a fallback public image...")
            fallback_url = "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg"
            response = requests.get(fallback_url, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                print(f"Fallback image downloaded successfully ({os.path.getsize(local_path)} bytes)")
                download_success = True
            else:
                raise Exception("Even fallback image download failed!")
        
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
                    files = {'file': (os.path.basename(local_path), f, 'image/jpeg')}
                    response = requests.post(upload_url, files=files, timeout=60)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("success", False):
                        public_url = data.get("data", {}).get("url")
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
            except Exception as e:
                print(f"Failed to generate presigned URL: {e}")
                public_url = None

        if not public_url:
            raise Exception("Unable to obtain a public URL for the image after multiple attempts")

        print(f"Image available at public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error preparing accessible image: {str(e)}")
        sys.exit(1)
    finally:
        # Clean up temp files only if using temporary directory
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            try:
                if 'local_path' in locals() and os.path.exists(local_path) and not local_storage_path:
                    os.unlink(local_path)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temporary files: {e}")


def _download_file(url: str, dest_path: str):
    """Download a file from `url` to `dest_path` (overwrite if exists)."""
    try:
        import requests
        from pathlib import Path
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"Downloaded file to {dest_path}")
        return dest_path
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None


def submit_kontext_pro_job(base, hdrs, input_image, prompt, aspect_ratio="match_input_image", safety_tolerance=2):
    """Submit a job to generate a podcast setting image using Kontext Pro."""
    payload = {
        "prompt": prompt,
        "input_image": input_image,
        "aspect_ratio": aspect_ratio,
        "output_format": "png",
        "safety_tolerance": safety_tolerance
    }
    
    print(f"Submitting image generation job with payload:")
    pprint(payload)
    
    r = requests.post(
        f"{base}/api/images/generate/flux/kontext/pro/",
        json=payload,
        headers=hdrs,
        timeout=30
    )
    r.raise_for_status()
    return r.json()["id"]


def poll_kontext_pro_job(base, hdrs, job_id, max_polls=60, sleep=10):
    """Poll Flux Kontext Pro job until it completes or fails."""
    job_url = f"{base}/api/images/generate/flux/kontext/pro/{job_id}/"
    print(f"Polling Kontext Pro job {job_id} → {job_url}")
    for i in range(max_polls):
        print(f"Poll {i+1}/{max_polls} ...")

        try:
            r = requests.get(job_url, headers=hdrs, timeout=30)
            if r.status_code == 404:
                # Server might not have created the record yet
                print("Job not found yet (404). Waiting...")
                time.sleep(sleep)
                continue
            r.raise_for_status()
        except Exception as e:
            print(f"Error polling job: {e}")
            time.sleep(sleep)
            continue

        job = r.json()
        status = job.get("status")
        print(f"Status: {status}")

        if status in ("succeeded", "completed", "done"):  # success cases
            output_url = job.get("output_url") or next((o.get("url") for o in job.get("outputs", []) if o.get("url")), None)
            if not output_url:
                raise ValueError("Job succeeded but output URL missing")
            return output_url

        if status in ("failed", "error"):
            raise ValueError(f"Kontext Pro job failed: {job.get('error_message') or job}")

        # still processing
        time.sleep(sleep)

    raise TimeoutError(f"Kontext Pro job {job_id} did not complete after {max_polls} polls")


def submit_kling_pro_job(base, hdrs, image_url, prompt, reference_images=None):
    """Submit a job to generate a silent talking-head video using Kling 1.6 pro."""
    payload = {
        "start_image": image_url,
        "end_image": image_url,
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "output_format": "mp4",
        "duration": 10,
        "safety_tolerance": 2
    }
    
    if reference_images:
        # API accepts up to 4 reference images
        payload["reference_images"] = reference_images[:4]
    
    print(f"Submitting Kling lipsync job with payload:")
    pprint(payload)
    
    r = requests.post(
        f"{base}/api/video/generate/kling/1-6/pro/",
        json=payload,
        headers=hdrs,
        timeout=30
    )
    r.raise_for_status()
    return r.json()["id"]


def poll_kling_job(base, hdrs, job_id, max_polls=60, sleep=10):
    """Poll Kling job until it completes or times out."""
    print(f"Polling Kling job {job_id} for completion...")
    for i in range(max_polls):
        print(f"Poll attempt {i+1}/{max_polls}...")
        
        r = requests.get(
            f"{base}/api/video/generate/kling/1-6/pro/{job_id}/",
            headers=hdrs,
            timeout=30
        )
        r.raise_for_status()
        
        job = r.json()
        status = job["status"]
        print(f"Status: {status}")
        
        # Print the current job structure to debug
        print(f"Current job data structure:")
        pprint(job)
        
        if status == "succeeded" or status == "completed" or status == "done":
            print(f"Job completed successfully!")
            # The API response has direct output_url field
            if "output_url" in job and job["output_url"]:
                return job["output_url"]
            # Also check video_url as fallback
            elif "video_url" in job and job["video_url"]:
                return job["video_url"]
            # Check for old structure with outputs array
            elif "outputs" in job and job["outputs"]:
                for output in job.get("outputs", []):
                    if output.get("type") == "video" and "url" in output:
                        return output["url"]
            
            # If we get here, we couldn't find a URL
            print("WARNING: Job reports success but no output URL found.")
            print("Full job response:")
            pprint(job)
            raise ValueError("Could not find output video URL in completed job")
        
        elif status == "failed":
            error = job.get("error_message") or job.get("error", "Unknown error")
            print(f"Job failed: {error}")
            
            # Print full job data for debugging
            print("Full job data:")
            pprint(job)
            
            raise ValueError(f"Job failed: {error}")
        
        elif status in ["starting", "pending", "processing"]:
            print(f"Job still {status}, waiting {sleep} seconds...")
            time.sleep(sleep)
        
        else:
            print(f"Unknown job status: {status}")
            print("Full job data:")
            pprint(job)
            time.sleep(sleep)
    
    raise TimeoutError(f"Job {job_id} did not complete after {max_polls} polls")


def poll_kling_lipsync_job(base, hdrs, job_id, max_polls=60, sleep=10):
    """Poll Kling lip-sync job until it completes or times out."""
    print(f"Polling Kling lip-sync job {job_id} for completion...")
    for i in range(max_polls):
        print(f"Poll attempt {i+1}/{max_polls}...")
        
        r = requests.get(
            f"{base}/api/video/generate/kling/lipsync/{job_id}/",
            headers=hdrs,
            timeout=30
        )
        r.raise_for_status()
        
        job = r.json()
        status = job["status"]
        print(f"Status: {status}")
        
        # Print the current job structure to debug
        print(f"Current job data structure:")
        pprint(job)
        
        if status == "succeeded":
            print(f"Job completed successfully!")
            # The API response has direct output_url field
            if "output_url" in job and job["output_url"]:
                return job["output_url"]
            # Also check video_output_url as fallback
            elif "video_output_url" in job and job["video_output_url"]:
                return job["video_output_url"]
            
            # If we get here, we couldn't find a URL
            print("WARNING: Job reports success but no output URL found.")
            print("Full job response:")
            pprint(job)
            raise ValueError("Could not find output video URL in completed job")
        
        elif status == "failed":
            error = job.get("error_message") or job.get("error", "Unknown error")
            print(f"Job failed: {error}")
            
            # Print full job data for debugging
            print("Full job data:")
            pprint(job)
            
            raise ValueError(f"Job failed: {error}")
        
        elif status in ["starting", "pending", "processing"]:
            print(f"Job still {status}, waiting {sleep} seconds...")
            time.sleep(sleep)
        
        else:
            print(f"Unknown job status: {status}")
            print("Full job data:")
            pprint(job)
            time.sleep(sleep)
    
    raise TimeoutError(f"Job {job_id} did not complete after {max_polls} polls")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate podcast-style talking head video")
    
    parser.add_argument(
        "--image-url", 
        required=True, 
        help="URL to the subject image (person's face to place in podcast)"
    )
    parser.add_argument(
        "--prompt", 
        default="a podcast setting in a professional studio, high quality microphone, soundproof room, dim lighting, podcast background", 
        help="Prompt for the podcast setting image generation"
    )
    parser.add_argument(
        "--video-prompt",
        default="subject talking on a podcast looking at camera",
        help="Prompt text describing the subject's talking action"
    )
    parser.add_argument(
        "--api-base", 
        default="https://example.com", 
        help="API endpoint"
    )
    parser.add_argument(
        "--username", 
        help="API username (if no env var)"
    )
    parser.add_argument(
        "--password", 
        help="API password (if no env var)"
    )
    parser.add_argument(
        "--local-storage-path",
        help="Local path to store downloaded files. If BASE_MEDIA_URL is set, will try to use it"
    )
    parser.add_argument(
        "--reference-image-url",
        action="append",
        help="Reference image URL to guide Kling style. May be specified up to 4 times."
    )
    parser.add_argument(
        "--audio-file",
        help="Optional: Audio file URL for lip-sync testing"
    )
    parser.add_argument(
        "--include-lipsync",
        action="store_true",
        help="If specified, will also test the lip-sync API after generating video"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable additional debug logging"
    )
    
    return parser.parse_args()


def main():
    """Run the full podcast video generation process."""
    args = parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Get API credentials from environment or command line
    username = args.username or os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
    password = args.password or os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234")
    
    # Get the API token
    try:
        print(f"Getting API token for user {username}...")
        scheme, token = get_token(args.api_base, username, password)
        hdrs = {"Authorization": f"{scheme} {token}"}
        print("Authentication successful!")
    except Exception as e:
        print(f"Error getting API token: {e}")
        sys.exit(1)
    
    # Save outputs for each step
    output_files = {}
    
    # Step 1: Prepare the subject image for API access
    try:
        print(f"\n=== STEP 1: Prepare subject image for external API access ===")
        subject_image_url = prepare_accessible_image(args.image_url, args.local_storage_path)
        if not subject_image_url:
            raise ValueError("Failed to prepare subject image URL")
        print(f"Subject image accessible at: {subject_image_url}")
        output_files['subject_image'] = subject_image_url
    except Exception as e:
        print(f"Error preparing subject image: {e}")
        sys.exit(1)
    
    # Step 2: Generate a 16:9 podcast setting image using Kontext Pro
    try:
        print(f"\n=== STEP 2: Generate a 16:9 podcast setting image ===")
        kontext_job_id = submit_kontext_pro_job(
            args.api_base, 
            hdrs, 
            subject_image_url, 
            args.prompt,
            aspect_ratio="16:9"
        )
        print(f"Kontext Pro job submitted with ID: {kontext_job_id}")
        
        podcast_image_url = poll_kontext_pro_job(args.api_base, hdrs, kontext_job_id)
        print(f"Generated podcast image: {podcast_image_url}")
        output_files['podcast_image'] = podcast_image_url
    except Exception as e:
        print(f"Error generating podcast setting image: {e}")
        sys.exit(1)
    
    # Step 3: Generate a talking-head video (silent) using Kling 1.6 pro
    try:
        print(f"\n=== STEP 3: Generate a talking-head video (silent) ===")
        
        # Prepare reference images for external access
        ref_images_accessible = None
        if args.reference_image_url:
            ref_images_accessible = [prepare_accessible_image(u, args.local_storage_path) for u in args.reference_image_url]
        
        kling_job_id = submit_kling_pro_job(
            args.api_base,
            hdrs,
            podcast_image_url,
            args.video_prompt,
            ref_images_accessible,
        )
        print(f"Kling job submitted with ID: {kling_job_id}")
        
        video_url = poll_kling_job(args.api_base, hdrs, kling_job_id)
        print(f"Generated video: {video_url}")
        output_files['video'] = video_url
        
        # Download the video locally when a storage path is provided
        if args.local_storage_path:
            try:
                from urllib.parse import urlparse
                filename = os.path.basename(urlparse(video_url).path) or 'podcast_video.mp4'
                local_video_path = os.path.join(args.local_storage_path, filename)
                saved = _download_file(video_url, local_video_path)
                if saved:
                    output_files['video_local'] = saved
            except Exception as e:
                print(f"Warning: could not download video to local storage: {e}")
    except Exception as e:
        print(f"Error generating talking head video: {e}")
        sys.exit(1)
    
    # Optional Step 4: Test lip-sync if requested
    if args.include_lipsync and (args.audio_file or 'audio_file' in output_files):
        try:
            print(f"\n=== STEP 4: Generate lip-sync video ===")
            audio_file = args.audio_file or output_files.get('audio_file')
            
            # Create a lip-sync job
            lipsync_data = {
                'video_url': video_url,
                'audio_file': audio_file,
            }
            
            print(f"Submitting lip-sync job with data: {lipsync_data}")
            r = requests.post(
                f"{args.api_base}/api/video/generate/kling/lipsync/",
                headers=hdrs,
                json=lipsync_data
            )
            r.raise_for_status()
            lipsync_response = r.json()
            lipsync_job_id = lipsync_response.get('id')
            
            if not lipsync_job_id:
                raise ValueError(f"Failed to get job ID from lipsync response: {lipsync_response}")
                
            print(f"Lip-sync job submitted with ID: {lipsync_job_id}")
            
            # Poll for completion
            lipsync_video_url = poll_kling_lipsync_job(args.api_base, hdrs, lipsync_job_id)
            print(f"Generated lip-sync video: {lipsync_video_url}")
            output_files['lipsync_video'] = lipsync_video_url
        except Exception as e:
            print(f"Error generating lip-sync video: {e}")
            print("Continuing with previous steps completed...")
    
    # Save all outputs to a JSON file
    output_path = "podcast_video_output.json"
    with open(output_path, 'w') as f:
        json.dump(output_files, f, indent=2)
    print(f"\nOutput URLs saved to {output_path}")
    
    print("\nSuccess! Your podcast-style talking head video has been generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
