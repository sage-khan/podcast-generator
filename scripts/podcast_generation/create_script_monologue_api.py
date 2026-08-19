#!/usr/bin/env python3
"""Test the `api/podcast/create/script/monologue` endpoint.

Example usage:
    python scripts/test_create_script_monologue.py \
        --prompt "The future of AI agents" \
        --speaker-name "Alice" \
        --api-base https://example.com \
        --username admin --password admin1234

The script will:
1. Authenticate and obtain an access token.
2. POST the payload to the endpoint.
3. Pretty-log the JSON response.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import requests

# Add project root for local execution so `scripts` can be run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from podcast_test_utils import (  # noqa: E402
    get_auth_headers,
    log_json,
    poll_job_status,
)

logger = logging.getLogger("test_create_script_monologue")


def parse_args():
    parser = argparse.ArgumentParser(description="Test monologue script generation endpoint")
    parser.add_argument("--prompt", required=True, help="Topic or idea for the podcast")
    parser.add_argument("--pdf", dest="pdf_path", help="Optional PDF file to attach (base64-encoded)")
    parser.add_argument("--speaker-name", default="Host", help="Speaker name (optional)")
    parser.add_argument("--api-base", default="http://localhost:8000", help="Base URL of the Django API")
    parser.add_argument("--username", default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"), help="API username")
    parser.add_argument("--password", default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234"), help="API password")
    parser.add_argument("--no-poll", action="store_true", help="Do not poll status after submission")
    return parser.parse_args()


def load_pdf_base64(pdf_path: Optional[str]) -> Optional[str]:
    if not pdf_path:
        return None
    import base64

    with open(pdf_path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode()
    logger.info("Loaded PDF %s (%d bytes)", pdf_path, len(encoded))
    return encoded


def main() -> int:
    args = parse_args()

    # Authenticate
    hdrs = get_auth_headers(args.api_base, args.username, args.password)
    hdrs["Content-Type"] = "application/json"

    payload = {
        "prompt": args.prompt,
        "speaker_name": args.speaker_name,
    }
    pdf_b64 = load_pdf_base64(args.pdf_path)
    if pdf_b64:
        payload["pdf_content"] = pdf_b64

    logger.info("POST %s/api/podcast/create/script/monologue with payload:", args.api_base)
    log_json("Request payload", payload)

    try:
        resp = requests.post(
            f"{args.api_base.rstrip('/')}/api/podcast/create/script/monologue",
            headers=hdrs,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        log_json("Response", data)
        job_id = data.get("id") or data.get("job_id")
        print("SUCCESS: Script generation job accepted. Job ID:", job_id)

        if not args.no_poll and job_id:
            poll_job_status(args.api_base, str(job_id), hdrs, interval=15, max_minutes=60)
        return 0
    except Exception as exc:
        logger.error("Request failed: %s", exc)
        if hasattr(exc, "response") and exc.response is not None:
            print("Response:", exc.response.text)
        return 1


if __name__ == "__main__":
    sys.exit(main())
