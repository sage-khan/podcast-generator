#!/usr/bin/env python3
"""Utilities shared by podcast_generator endpoint test scripts.

Features:
- Loads environment variables from project .env and .env-do files.
- Provides `get_auth_headers` to obtain JWT or token auth header.
- Wraps DigitalOcean Spaces URL conversion using `storage_client.get_accessible_url`.
- Configures rich logging format at INFO level by default.
"""
import logging
import os
import pathlib
import sys
from urllib.parse import urlparse

# Configure logging first
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("podcast_test_utils")

# ---------------------------------------------------------------------------
# Environment loading (project root .env + .env-do)
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Load .env and .env-do files
from dotenv import load_dotenv
for dot_env in (PROJECT_ROOT / ".env", PROJECT_ROOT / ".env-do"):
    if dot_env.exists():
        logger.info("Loading environment variables from %s", dot_env)
        load_dotenv(dotenv_path=dot_env, override=True)

# Verify DO Spaces credentials are loaded
do_key = os.environ.get('DO_SPACES_KEY')
do_secret = os.environ.get('DO_SPACES_SECRET')
do_region = os.environ.get('DO_SPACES_REGION', 'nyc3')
do_endpoint = os.environ.get('DO_SPACES_ENDPOINT', 'https://nyc3.digitaloceanspaces.com')

logger.info("Digital Ocean credentials: KEY=%s, SECRET=%s, REGION=%s, ENDPOINT=%s", 
           "set" if do_key else "MISSING", 
           "set" if do_secret else "MISSING",
           do_region, do_endpoint)

# Add project root to PYTHONPATH
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the storage client (will work now that PROJECT_ROOT is in sys.path)
try:
    from shared.clients.storage_client import storage_client
    logger.info("Successfully imported storage_client")
except Exception as e:
    logger.warning(f"Failed to import storage_client: {e}")
    storage_client = None

# Create boto3 client for DO Spaces (as fallback)
import boto3
try:
    s3_client = boto3.client(
        's3',
        region_name=do_region,
        endpoint_url=do_endpoint,
        aws_access_key_id=do_key,
        aws_secret_access_key=do_secret
    )
    logger.info("Successfully created S3 client for DO Spaces")
except Exception as e:
    logger.error(f"Error creating S3 client: {e}")
    s3_client = None

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
import requests

def get_auth_headers(base_url: str, username: str, password: str) -> dict:
    """Get token authentication headers from Django JWT or DRF token endpoint."""
    logger.info("Authenticating to %s as %s", base_url, username)
    
    # Support base URL variants
    base_urls = [base_url]
    if "example.com" in base_url:
        # Try both the cc and ccapi variants
        if "ccapi" not in base_url:
            base_urls.append(base_url.replace("example.com", "example.com"))
        else:
            base_urls.append(base_url.replace("example.com", "example.com"))
    
    # Potential auth endpoints to try
    endpoints = [
        ("/api/token/", "jwt", "access"),       # Django Simple JWT
        ("/api-token-auth/", "token", "token"), # Django Rest Framework Token
        ("/api/auth/token/", "jwt", "access"),  # Custom JWT endpoint
        ("/api/v1/auth/token/", "jwt", "access"), # Versioned API endpoint
        ("/auth/token/", "jwt", "access"),      # Another common pattern
    ]
    
    for base in base_urls:
        for endpoint_path, auth_type, token_key in endpoints:
            full_url = f"{base}{endpoint_path}"
            try:
                logger.debug("Trying auth endpoint: %s", full_url)
                r = requests.post(
                    full_url,
                    data={"username": username, "password": password},
                    timeout=30,
                )
                
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if token_key in data:
                            token_value = data[token_key]
                            auth_header = f"{'Bearer' if auth_type == 'jwt' else 'Token'} {token_value}"
                            logger.info("Authentication successful using %s", full_url)
                            return {"Authorization": auth_header}
                    except ValueError:
                        logger.debug("Response not valid JSON: %s", r.text[:100])
                else:
                    logger.debug("Auth failed with status %d: %s", r.status_code, r.text[:100])
            
            except Exception as e:
                logger.debug("Auth request to %s failed: %s", full_url, str(e))
    
    # If we get here, all auth attempts failed
    logger.error("Failed to authenticate with any known endpoint")
    logger.info("Please verify the API base URL, username, and password are correct")
    raise RuntimeError("Failed to obtain auth token using known endpoints")

def make_accessible_url(url: str, expires_in: int = 3600) -> str:
    """Convert DigitalOcean Spaces URL to publicly accessible URL.
    
    For CDN URLs (already public), returns the URL unchanged.
    For private DO Spaces URLs, generates a presigned URL.
    """
    # Skip conversion for CDN URLs (already public)
    if "cdn.digitaloceanspaces.com" in url:
        logger.info("URL is already public (CDN): %s", url)
        return url
        
    # Try using the storage_client if available
    if storage_client:
        try:
            logger.info("Converting DO Spaces URL to accessible using storage_client: %s", url)
            accessible = storage_client.get_accessible_url(url, expires_in=expires_in)
            logger.info("Converted to: %s", accessible)
            return accessible
        except Exception as e:
            logger.warning(f"storage_client.get_accessible_url failed: {e}")
    
    # Fall back to direct boto3 presigning if storage_client failed or isn't available
    if s3_client:
        try:
            parsed = urlparse(url)
            bucket = parsed.netloc.split(".")[0]
            key = parsed.path.lstrip("/")
            
            logger.info(f"Generating presigned URL via boto3 for bucket={bucket}, key={key}")
            presigned = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned URL: {presigned}")
            return presigned
        except Exception as e:
            logger.error(f"Failed to generate presigned URL with boto3: {e}")
    
    # If all else fails, return the original URL
    logger.warning("All URL conversion methods failed, returning original URL")
    return url

def log_json(title: str, obj, *, print_also: bool = True):
    """Pretty-print JSON-serializable object with a title."""
    import json
    
    json_str = json.dumps(obj, indent=2)
    
    logger.info("%s: %s", title, json_str)
    
    if print_also:
        print(f"\n{title}:\n{json_str}\n")

import time
def poll_job_status(base_url: str, job_id: str, auth_headers: dict, 
                    max_minutes: int = 120, interval_seconds: int = 30,
                    job_type: str = "podcast"):
    """Poll job status endpoint until completion or timeout."""
    max_polls = (max_minutes * 60) // interval_seconds
    
    for poll_num in range(1, max_polls + 1):
        logger.info("Polling job status (%d/%d)...", poll_num, max_polls)
        
        try:
            if job_type == "podcast":
                url = f"{base_url}/api/podcast/status/{job_id}"
            else:
                url = f"{base_url}/api/{job_type}/status/{job_id}"
                
            r = requests.get(url, headers=auth_headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            log_json(f"Job status (poll {poll_num}/{max_polls})", data)
            
            if data.get("status") in ("completed", "failed", "error"):
                logger.info("Job %s with final status: %s", 
                          "SUCCEEDED" if data.get("status") == "completed" else "FAILED",
                          data.get("status"))
                return data
                
        except Exception as e:
            logger.error("Error polling job status: %s", e)
        
        logger.info("Waiting %d seconds before next poll...", interval_seconds)
        time.sleep(interval_seconds)
        
    logger.warning("Polling timed out after %d minutes", max_minutes)
    return None

# For testing this module directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test podcast utility functions")
    parser.add_argument("--test-url", help="Test URL conversion")
    parser.add_argument("--print-token", action="store_true", help="Print auth token")
    parser.add_argument("--username", default=os.getenv("DJANGO_SUPERUSER_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin1234"))
    parser.add_argument("--api-base", default="http://localhost:8000")
    
    args = parser.parse_args()
    
    if args.print_token:
        headers = get_auth_headers(args.api_base, args.username, args.password)
        print(f"Auth header: {headers['Authorization']}")
        
    if args.test_url:
        print(f"Original URL: {args.test_url}")
        print(f"Accessible URL: {make_accessible_url(args.test_url)}")
