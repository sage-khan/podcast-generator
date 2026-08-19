#!/usr/bin/env python
"""Standalone client script to edit a *single* image with the Flux Kontext Pro
model hosted by the image_generation service.

This mirrors the behaviour of `edit_image_kontext_multi_list.py` but for the
single-image endpoint documented in `documentation/flux-kontext-pro.md`.

Key features
────────────
1. Authenticates against `/api/token/` (supports both SimpleJWT and DRF
   TokenAuth) using `API_USERNAME` / `API_PASSWORD` env vars or corresponding
   CLI flags.
2. Supports DigitalOcean Spaces URLs – converts to a presigned public URL via
   the shared `storage_client` so Replicate can fetch the asset.
3. Submits a generation job to `/api/images/generate/flux/kontext/pro/` and
   polls the status route until completion.
4. Robustly extracts the output image URL, downloads the file, and saves it to
   `--output_dir` with a timestamped, prompt-derived file name.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Allow `from shared.clients.storage_client import storage_client` without Django
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))
from shared.clients.storage_client import storage_client  # type: ignore

# ---------------------------------------------------------------------------
# Configuration & constants
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

VALID_ASPECT_RATIOS = {
    "match_input_image",
    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
    "4:5", "5:4", "21:9", "9:21", "2:1", "1:2",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_auth_token(base_url: str, username: str, password: str) -> Tuple[str, str]:
    """Return `(token, scheme)` where *scheme* is either `Bearer` or `Token`."""
    auth_url = f"{base_url.rstrip('/')}/api/token/"
    response = requests.post(auth_url, data={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "access" in data:  # SimpleJWT
        return data["access"], "Bearer"
    if "token" in data:  # DRF TokenAuth
        return data["token"], "Token"

    raise RuntimeError(f"Unexpected auth response: {data}")


def submit_generation_job(
    base_url: str,
    headers: dict,
    *,
    input_image: str,
    prompt: str,
    aspect_ratio: str,
    seed: int | None,
    output_format: str,
    safety_tolerance: int,
) -> Tuple[str, str]:
    """Submit a single-image edit job and return `(job_id, endpoint_path)`."""
    endpoint = "/api/images/generate/flux/kontext/pro/"
    payload: dict = {
        "input_image": input_image,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "safety_tolerance": safety_tolerance,
    }
    if seed is not None:
        payload["seed"] = seed

    response = requests.post(urljoin(base_url, endpoint), json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    job_id = response.json().get("id")
    if not job_id:
        raise RuntimeError(f"API response missing job ID: {response.text}")

    logging.info("Submitted job %s", job_id)
    return job_id, endpoint


def poll_until_complete(base_url: str, headers: dict, endpoint: str, job_id: str) -> str:
    """Poll the status route until finished; return the output image URL."""
    status_url = f"{base_url.rstrip('/')}{endpoint}{job_id}/"
    while True:
        response = requests.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        status = data.get("status", "").lower()
        logging.info("Job %s → %s", job_id, status)

        if status in {"succeeded", "completed"}:
            url = (
                data.get("output_url")
                or (data.get("output") if isinstance(data.get("output"), str) else None)
                or (data.get("output")[0] if isinstance(data.get("output"), list) else None)
                or (data.get("output_urls")[0] if isinstance(data.get("output_urls"), list) else None)
            )
            if not url:
                raise RuntimeError("Job completed but no output URL present in response")
            return url

        if status in {"failed", "error"}:
            raise RuntimeError(f"Generation failed: {data.get('error', 'Unknown error')}")

        time.sleep(10)


def download_file(url: str, destination: Path) -> None:
    """Stream-download *url* to *destination*."""
    logging.info("Downloading result → %s", destination)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with destination.open("wb") as fp:
            for chunk in resp.iter_content(chunk_size=8192):
                fp.write(chunk)

# ---------------------------------------------------------------------------
# CLI parsing & main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit a single image using Flux Kontext Pro")
    parser.add_argument("--subject_image_url", required=True, help="URL of the image to edit")
    parser.add_argument("--prompt", required=True, help="Editing prompt / instruction")
    parser.add_argument("--aspect_ratio", default="match_input_image", help="Desired output aspect ratio")
    parser.add_argument("--seed", type=int, help="Optional random seed for reproducibility")
    parser.add_argument("--output_format", default="png", choices=["png", "jpg", "jpeg", "webp"], help="Image format")
    parser.add_argument("--safety_tolerance", type=int, default=2, choices=list(range(0, 7)), help="Safety tolerance (0–6)")
    parser.add_argument("--output_dir", default="./media/output/images", help="Directory to save the generated image")
    parser.add_argument("--api_base_url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--username", default=os.getenv("API_USERNAME"))
    parser.add_argument("--password", default=os.getenv("API_PASSWORD"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.aspect_ratio not in VALID_ASPECT_RATIOS:
        logging.error("Invalid aspect_ratio %s. Allowed values: %s", args.aspect_ratio, ", ".join(sorted(VALID_ASPECT_RATIOS)))
        sys.exit(1)

    if not (args.username and args.password):
        logging.error("API username & password are required (flags or env vars)")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure DigitalOcean URLs are publicly accessible
    subject_url = args.subject_image_url
    if "digitaloceanspaces.com" in subject_url:
        subject_url = storage_client.get_accessible_url(subject_url)
        logging.info("Converted subject URL to presigned link")

    try:
        token, scheme = get_auth_token(args.api_base_url, args.username, args.password)
        headers = {"Authorization": f"{scheme} {token}", "Content-Type": "application/json"}

        job_id, endpoint = submit_generation_job(
            args.api_base_url,
            headers,
            input_image=subject_url,
            prompt=args.prompt,
            aspect_ratio=args.aspect_ratio,
            seed=args.seed,
            output_format=args.output_format,
            safety_tolerance=args.safety_tolerance,
        )

        result_url = poll_until_complete(args.api_base_url, headers, endpoint, job_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = os.path.splitext(result_url.split("?")[0])[1] or f".{args.output_format}"
        prompt_stub = "".join(c for c in args.prompt if c.isalnum() or c in (" ", "_"))[:50].strip().replace(" ", "_")
        destination = output_dir / f"edited_image_{prompt_stub}_{timestamp}{extension}"

        download_file(result_url, destination)
        print(f"Image saved to: {destination}")
    except Exception as exc:
        logging.error("Error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()