#!/usr/bin/env python3
"""
Fire-and-forget test of the Minimax Speech-02-HD endpoint.

Usage:
  python test_minimax_speech_generation.py \
      --base-url https://example.com \
      --user admin --password admin1234 \
      --text "Hello world, this is a test" \
      --voice Wise_Woman \
      --language-boost English
"""
import argparse, os, sys, time, json, requests
from pprint import pprint

def get_token(base, user, pwd):
    """Return (scheme, token_str) for Authorization header.

    Supports both response formats:
        {"access": "<jwt>"}  -> scheme "Bearer"
        {"token":  "<token>"} -> scheme "Token"
    """
    # DRF obtain_auth_token expects form data, not JSON.
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

def submit_job(base, hdrs, payload):
    r = requests.post(f"{base}/api/audio/generate/minimax/speech-02-hd/",
                      json=payload, headers=hdrs, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def poll(base, hdrs, job_id, sleep=5):
    url = f"{base}/api/audio/generate/minimax/speech-02-hd/{job_id}/"
    while True:
        r = requests.get(url, headers=hdrs, timeout=30); r.raise_for_status()
        data = r.json(); status = data["status"]
        print(f"[{time.strftime('%X')}] {job_id} – {status}")
        if status in ("succeeded", "failed", "error"):
            pprint(data); return
        time.sleep(sleep)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="https://example.com")
    p.add_argument("--user", required=True); p.add_argument("--password", required=True)
    p.add_argument("--text", required=True); p.add_argument("--voice", default="Wise_Woman")
    p.add_argument("--language-boost", default="English", 
                  help="Language boost parameter. Valid options: None, Automatic, English, Chinese, Spanish, etc.")
    args = p.parse_args()

    scheme, token = get_token(args.base_url, args.user, args.password)
    headers = {"Authorization": f"{scheme} {token}"}

    job_id = submit_job(
        args.base_url,
        headers,
        {"text": args.text, "voice_id": args.voice, "language": "en", "language_boost": args.language_boost}
    )
    print("Job submitted:", job_id)
    poll(args.base_url, headers, job_id)