#!/usr/bin/env python3
"""
Simple standalone script to verify that our `StorageClient` can correctly access and download
files stored in DigitalOcean Spaces.

The script performs the following steps:
1. Generates an accessible (public or pre-signed) URL for the supplied Spaces object.
2. Downloads the object to a temporary file to confirm access.
3. Logs the result and exits with a non-zero status code on failure.

Usage:
    python scripts/test_do_spaces_connection.py --url https://my-space.nyc3.cdn.digitaloceanspaces.com/path/to/object.ext

If no `--url` is supplied, a default public sample object is used.

Environment variables required (or set in your .env):
    DO_SPACES_KEY, DO_SPACES_SECRET, DO_SPACES_REGION, DO_SPACES_BUCKET,
    DO_SPACES_ENDPOINT / DO_SPACES_CDN_ENDPOINT / DO_SPACES_ORIGIN_ENDPOINT
"""
import argparse
import logging
import os
import sys
import tempfile
import pathlib
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables from .env file BEFORE importing storage_client
env_path = pathlib.Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    logger.info(f"Loading environment from {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(f"No .env file found at {env_path}")

# Ensure we use DO Spaces backend for this test unless explicitly overridden
if not os.getenv("STORAGE_BACKEND"):
    os.environ["STORAGE_BACKEND"] = "do_spaces"

# Verify required DO Spaces credentials are available
required_vars = ['DO_SPACES_KEY', 'DO_SPACES_SECRET', 'DO_SPACES_REGION', 'DO_SPACES_BUCKET']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Please set these in your .env file or environment")
    sys.exit(1)
else:
    logger.info(f"DO credentials found: KEY={os.getenv('DO_SPACES_KEY')[:4]}..., BUCKET={os.getenv('DO_SPACES_BUCKET')}")

# Ensure project root is on PYTHONPATH so we can import shared.* when running this file directly
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import storage_client AFTER environment variables are loaded
from shared.clients.storage_client import storage_client


def main():
    parser = argparse.ArgumentParser(
        description="Test DigitalOcean Spaces access via StorageClient",
        epilog="Ensure DO Spaces credentials are set in environment variables or .env file."
    )
    parser.add_argument(
        "--url",
        help="DigitalOcean Spaces object URL to test",
        default="https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/audio/R8_WQTHN3AP.wav",
    )
    parser.add_argument(
        "--expires",
        type=int,
        default=3600,
        help="Presigned URL expiry time in seconds (only used if the object is private).",
    )
    args = parser.parse_args()

    test_url = args.url
    logger.info(f"Testing StorageClient with URL: {test_url}")

    try:
        # Step 1: Get public or presigned URL
        accessible_url = storage_client.get_accessible_url(test_url, expires_in=args.expires)
        logger.info(f"Accessible URL obtained: {accessible_url}")

        # Step 2: Download the file to a temporary path
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        download_result = storage_client.download_file(accessible_url, tmp_path)
        if not download_result:
            logger.error("Download failed - empty result returned")
            print("ERROR: Download failed")
            sys.exit(1)
            
        file_size = os.path.getsize(tmp_path)
        logger.info(f"Downloaded file to {tmp_path} ({file_size} bytes)")
        
        if file_size == 0:
            logger.error("Downloaded file is empty (0 bytes)")
            print("ERROR: Downloaded file is empty")
            sys.exit(1)

        print(f"SUCCESS: DigitalOcean Spaces object downloaded successfully! ({file_size} bytes)")
    except Exception as e:
        logger.error(f"Failed to access or download file: {e}")
        print("ERROR:", e)
        sys.exit(1)

    
if __name__ == "__main__":
    main()