#!/usr/bin/env python3
"""Test the `api/podcast/create/script/dialogue` endpoint.

Example:
    python scripts/test_create_script_dialogue.py \
        --prompt "Benefits of remote work" \
        --speaker1 "Alice" --speaker2 "Bob" \
        --api-base https://example.com
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from podcast_test_utils import get_auth_headers, log_json, poll_job_status  # noqa: E402

logger = logging.getLogger("test_create_script_dialogue")


def parse_args():
    p = argparse.ArgumentParser(description="Test dialogue script generation endpoint")
    p.add_argument("--prompt", required=True)
    p.add_argument("--pdf", dest="pdf_path")
    p.add_argument("--speaker1", required=True, help="Name of first speaker")
    p.add_argument("--speaker2", required=True, help="Name of second speaker")
    p.add_argument("--api-base", default="http://localhost:8000")
    p.add_argument("--username", default=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"))
    p.add_argument("--password", default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin1234"))
    p.add_argument("--no-poll", action="store_true", help="Do not poll status after submission")
    return p.parse_args()


def load_pdf_base64(path: Optional[str]):
    if not path:
        return None
    import base64, pathlib
    b = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    logger.info("Loaded PDF %s (%d bytes b64)", path, len(b))
    return b


def main() -> int:
    args = parse_args()
    hdrs = get_auth_headers(args.api_base, args.username, args.password)
    hdrs["Content-Type"] = "application/json"

    payload = {
        "prompt": args.prompt,
        "speaker1_name": args.speaker1,
        "speaker2_name": args.speaker2,
    }
    pdf_b64 = load_pdf_base64(args.pdf_path)
    if pdf_b64:
        payload["pdf_content"] = pdf_b64

    log_json("Request payload", payload)
    try:
        r = requests.post(f"{args.api_base.rstrip('/')}/api/podcast/create/script/dialogue", headers=hdrs, json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        log_json("Response", data)
        job_id = data.get("id") or data.get("job_id")
        print("SUCCESS: Dialogue script job accepted. Job ID:", job_id)

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
