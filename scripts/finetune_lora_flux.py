# sample command
# python finetune_lora_flux.py https://aicc.nyc3.cdn.digitaloceanspaces.com/pose_generation/output/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f-poses.zip
# python finetune_lora_flux.py https://aicc.nyc3.digitaloceanspaces.com/aicc/pose_generation/output/b1bb5a8a-c0ea-47dc-a104-833779ddb3ce/b1bb5a8a-c0ea-47dc-a104-833779ddb3ce-poses.zip

import os
import sys
import time
import logging
import requests
from urllib.parse import urlparse
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─── CONFIG ─────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger()

# For testing - set to False to use HTTP instead of HTTPS temporarily
USE_HTTPS = True

API_BASE = os.getenv("DOMAIN", "example.com")  # Using IP directly for testing
PROTOCOL = "https://" if USE_HTTPS else "http://"
DOMAIN = f"{PROTOCOL}{API_BASE}"
# Updated API endpoints for the new modular structure
START_URL = f"{DOMAIN}/api/model-training/finetune/lora/"
DETAIL_URL = f"{DOMAIN}/api/model-training/finetune/lora/{{job_id}}/"
HEADERS = {"Content-Type": "application/json"}

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_OWNER = os.getenv("REPLICATE_OWNER", "your-replicate-username")
if not REPLICATE_API_TOKEN:
    logger.error("Please set REPLICATE_API_TOKEN")
    sys.exit(1)

# ─── HELPERS ────────────────────────────────────────────────
def extract_basename(url: str) -> str:
    """
    Extract the base name (36-character hash) from the URL.
    For example, from a URL containing '5efae35268239f620f35e315c1df361f2fa75e89-poses.zip',
    this will extract '5efae35268239f620f35e315c1df361f2fa75e89'.
    """
    # Get the last part of the URL (the filename)
    filename = os.path.basename(urlparse(url).path)
    
    # Remove the "-poses.zip" suffix if present
    if filename.endswith("-poses.zip"):
        return filename.replace("-poses.zip", "")
    
    # Otherwise just return the filename without extension
    return os.path.splitext(filename)[0]

def start_job(zip_url: str, steps: int = 1000, lora_rank: int = 16, client_webhook_url: str = None) -> dict:
    # Extract the base hash from the URL
    base_hash = extract_basename(zip_url)
    
    payload = {
        "model_name": base_hash,
        "trigger_word": base_hash,
        "input_image_urls": [zip_url],
        "steps": steps,
        "lora_rank": lora_rank
    }
    
    # Add client webhook URL if provided
    if client_webhook_url:
        payload["client_webhook_url"] = client_webhook_url
        
    logger.info("→ POST %s %s", START_URL, payload)
    r = requests.post(START_URL, json=payload, headers=HEADERS, timeout=120)
    r.raise_for_status()
    data = r.json()
    logger.info("← %s", data)
    return data

def poll_job(job_id: str, interval: int = 10) -> dict:
    url = DETAIL_URL.format(job_id=job_id)
    while True:
        logger.info("→ GET %s", url)
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        job = r.json()
        status = job.get("status")
        logger.info("Job status: %s", status)
        if status in ("succeeded", "failed", "canceled"):
            return job
        time.sleep(interval)

def poll_replicate(training_id: str, interval: int = 10) -> dict:
    url = f"https://api.replicate.com/v1/trainings/{training_id}"
    headers = {"Authorization": f"Token {REPLICATE_API_TOKEN}"}
    last = ""
    while True:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        d = r.json()
        logs = d.get("logs", "")
        if logs and logs != last:
            logger.info("–– Replicate logs ––\n%s", logs)
            last = logs
        status = d.get("status")
        logger.info("Replicate status: %s", status)
        if status in ("succeeded", "failed", "canceled"):
            return d
        time.sleep(interval)

# ─── MAIN ───────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune a LoRA model through the the podcast-generator API")
    parser.add_argument("zip_url", help="URL to the ZIP file containing training images")
    parser.add_argument("--steps", type=int, default=1000, help="Number of training steps (default: 1000)")
    parser.add_argument("--lora-rank", type=int, default=16, help="LoRA rank parameter (default: 16)")
    parser.add_argument("--client-webhook", type=str, help="Optional client webhook URL for status updates")
    parser.add_argument("--wait", type=int, default=30, help="Max seconds to wait for Replicate ID assignment (default: 30)")
    
    args = parser.parse_args()

    # Start the job and return immediately - webhook will handle status updates
    job = start_job(args.zip_url, steps=args.steps, lora_rank=args.lora_rank, client_webhook_url=args.client_webhook)
    job_id = job.get("id")
    training_id = job.get("replicate_training_id")
    if not job_id:
        logger.error("No job ID returned, aborting.")
        sys.exit(1)

    logger.info("✅ Job started successfully!")
    logger.info("Job ID: %s", job_id)
    
    # Poll for the Replicate ID if it's not available immediately
    wait_time = 0
    max_wait = args.wait  # Maximum time to wait in seconds
    poll_interval = 3  # Seconds between polling attempts
    
    if not training_id:
        logger.info("Waiting for Replicate Training ID to be assigned (max %d seconds)...", max_wait)
        while not training_id and wait_time < max_wait:
            time.sleep(poll_interval)
            wait_time += poll_interval
            
            # Query job status to check for replicate_training_id
            url = DETAIL_URL.format(job_id=job_id)
            try:
                r = requests.get(url, headers=HEADERS)
                r.raise_for_status()
                updated_job = r.json()
                training_id = updated_job.get("replicate_training_id")
                if training_id:
                    logger.info("Replicate Training ID assigned after %d seconds", wait_time)
            except Exception as e:
                logger.warning("Error polling for training ID: %s", e)
    
    logger.info("Replicate Training ID: %s", training_id)
    
    # Display client webhook URL if provided
    if args.client_webhook:
        logger.info("Client Webhook URL: %s", args.client_webhook)
        logger.info("Status updates will be sent to your webhook URL when the job status changes")
    else:
        logger.info("Status updates will be handled by server-side webhook callbacks.")
    
    # Add detailed information on how to check job status
    logger.info("\n----- HOW TO CHECK JOB STATUS -----")
    logger.info("1. On Replicate (requires login with %s account):", REPLICATE_OWNER)
    logger.info("   🔗 https://replicate.com/p/%s", training_id)
    
    logger.info("\n2. Through the API (no login required):")
    logger.info("   🔗 %s/api/model-training/finetune/lora/%s", API_BASE, job_id)
    logger.info("   Command: curl %s/api/model-training/finetune/lora/%s", API_BASE, job_id)
    logger.info("---------------------------------\n")
    
    logger.info("You can check the job status at: %s/api/model-training/finetune/lora/%s/", API_BASE, job_id)

"""
Verify completion - Updated to use the new model structure

from model_training.models import LoraTrainingJob
job = LoraTrainingJob.objects.get(id='f7d55cab-a4ad-4c28-a5d5-8097c34ccde7')
print(job.status, job.replicate_model_version)
"""