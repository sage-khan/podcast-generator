#!/usr/bin/env python3
"""
Create a podcast monologue project and generate a script.

Example:
  python scripts/podcast_generation/test_create_podcast_monologue.py \
      --project-id my-podcast \
      --prompt "In ~30 seconds, talk about AI in digital marketing" \
      --speaker-name Austin \
      --pdf-url https://aicc.nyc3.cdn.digitaloceanspaces.com/pdfs/context.pdf \
      --upload-to-do
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
from pathlib import Path
import logging
import boto3
from datetime import datetime
import subprocess
from threading import Thread
from queue import Queue, Empty
from shared.utils import merge_videos

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('podcast_monologue_test')

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
except Exception as e:
    print(f"Failed to create S3 client: {e}")
    s3_client = None

def make_space_url_accessible(url):
    """Generate a presigned URL for a DO Spaces object if needed."""
    if not url or not s3_client:
        return url
    
    # Skip if it's already a public CDN URL    
    if "cdn.digitaloceanspaces.com" in url:
        print(f"URL is already publicly accessible (CDN): {url}")
        return url
    
    # Skip if not a DO Spaces URL
    if "digitaloceanspaces.com" not in url:
        return url
    
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    # Extract the bucket name from hostname (e.g., "aicc" from "aicc.nyc3.digitaloceanspaces.com")
    bucket = parsed.netloc.split('.')[0]
    
    # Extract the key (object path) - remove leading slash
    key = parsed.path.lstrip('/')
    
    print(f"Generating presigned URL for bucket={bucket}, key={key}")
    
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600  # URL valid for 1 hour
        )
        print(f"Presigned URL generated successfully")
        return presigned_url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return url

def upload_file_to_do_spaces(file_path, bucket, object_name=None):
    """Upload a file to a DO Spaces bucket."""
    if not s3_client:
        logger.error("S3 client not configured. Cannot upload file.")
        return None

    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3_client.upload_file(str(file_path), bucket, object_name)
        url = f"https://{bucket}.{os.environ.get('DO_SPACES_REGION', 'nyc3')}.cdn.digitaloceanspaces.com/{object_name}"
        logger.info(f"Successfully uploaded {file_path.name} to {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to upload {file_path.name}: {e}")
        return None

def download_pdf(url, project_path):
    """Download a PDF from a URL and save it to the project path."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        # Save PDF content to a temporary file
        temp_pdf_path = project_path / "context.pdf"
        with open(temp_pdf_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"PDF downloaded and saved to {temp_pdf_path}")
        return temp_pdf_path
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return None

def _enqueue_output(stream, q):
    for line in iter(stream.readline, ''):
        q.put(line)
    stream.close()

def run_subprocess_stream(cmd_list):
    """Run a subprocess, stream its combined stdout/stderr to logger in real time, and return (stdout_str, returncode)."""
    logger.info(f"EXEC >> {' '.join(cmd_list)}")
    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    q = Queue()
    t = Thread(target=_enqueue_output, args=(proc.stdout, q))
    t.daemon = True  # thread dies with the program
    t.start()

    collected = []
    while True:
        try:
            line = q.get_nowait()
        except Empty:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        logger.info(line.rstrip())
        collected.append(line)

    proc.wait()
    stdout_str = ''.join(collected)
    return stdout_str, proc.returncode

def main():
    parser = argparse.ArgumentParser(description="Create a podcast monologue project and generate a script.")
    parser.add_argument("--project-id", help="A unique ID for the project (not required when --project-folder is provided).")
    parser.add_argument("--prompt", help="Prompt for the monologue content (required unless --edit-image is used).")
    parser.add_argument("--speaker-name", help="Name of the speaker (optional if detectable from existing project folder).")
    parser.add_argument("--pdf-url", help="URL to an optional PDF file for context (e.g., on DO Spaces).")
    parser.add_argument("--script-number", type=int, default=1, help="The script number for this monologue.")
    parser.add_argument("--upload-to-do", action="store_true", help="Upload generated files to DigitalOcean Spaces.")
    parser.add_argument("--project-folder", help="Path to an existing project folder to use.")
    parser.add_argument("--generate-voice-clone", action="store_true", help="Create/ensure a voice clone for the speaker.")
    parser.add_argument("--generate-TTS", action="store_true", help="Generate TTS audio from the monologue.")
    parser.add_argument("--voice-id", help="Existing voice ID to use for audio generation.")
    parser.add_argument("--sample-audio-url", help="URL of the sample audio for voice cloning (if no --voice-id).")
    parser.add_argument("--api-base-url", default=os.environ.get("API_BASE_URL", "https://example.com"), help="Base URL for the the podcast-generator API used by TTS generation.")
    parser.add_argument("--tts-model", default="speech-02-hd", choices=["speech-02-hd", "speech-02-HD", "speech-02-turbo"], help="TTS model version to use.")
    parser.add_argument("--edit-image", action="store_true", help="Generate the podcast cover image as part of the pipeline.")
    # Support both --edit-image-only (preferred) and legacy --image-only
    parser.add_argument("--edit-image-only", "--image-only", dest="image_only", action="store_true",
                        help="Run only the image pipeline and then exit (alias: --image-only).")
    parser.add_argument("--subject-image-url", help="URL of the subject image for editing/composition.")
    parser.add_argument("--background-image-url", help="URL of the background image (optional; triggers multi-image composition).")
    parser.add_argument("--image-prompt", help="Prompt describing the desired edit or composition.")
    parser.add_argument("--image-aspect-ratio", default="match_input_image", help="Aspect ratio for the generated image.")
    parser.add_argument("--image-output-format", default="png", choices=["png", "jpg", "jpeg", "webp"], help="Output format for the generated image.")
    parser.add_argument("--image-seed", type=int, help="Optional random seed for reproducibility.")
    parser.add_argument("--image-safety-tolerance", type=int, default=2, choices=[0, 1, 2], help="Safety tolerance level (0=strict, 2=permissive).")
    # NEW: video generation flags
    parser.add_argument("--img2vid-silent", dest="img2vid_silent", action="store_true", help="Generate a silent talking-head video (Kling 1.6 Pro) after image step.")
    parser.add_argument("--video-prompt", default="subject talking on a podcast looking at camera", help="Prompt text to pass to Kling video generation.")
    # NEW: lipsync integration flag
    parser.add_argument("--generate-lipsync", action="store_true", help="Create lip-sync videos using Kling lip-sync API")
    parser.add_argument("--audio-dir", help="Directory containing local audio files (.wav/.mp3 etc.) for lipsync")
    # API auth (optional; falls back to env vars)
    parser.add_argument("--username", help="API username for authentication (optional; defaults to $API_USERNAME).")
    parser.add_argument("--password", help="API password for authentication (optional; defaults to $API_PASSWORD).")
    
    args = parser.parse_args()

    # Validate basic input combinations
    if not args.project_id and not args.project_folder:
        logger.error("You must specify either --project-id or --project-folder")
        return 1

    # 1. Setup project folder
    if args.project_folder:
        project_path = Path(args.project_folder)
        if not project_path.exists():
            logger.info(f"Project folder not found. Creating: {project_path}")
            try:
                project_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create project folder: {e}")
                return 1
        elif not project_path.is_dir():
            logger.error(f"Error: The path provided for --project-folder exists but is not a directory: {args.project_folder}")
            return 1
        logger.info(f"Using existing project folder: {project_path}")
        project_folder_name = project_path.name

        # Attempt to derive project_id from folder prefix before '--'
        if not args.project_id:
            args.project_id = project_folder_name.split('--')[0]
            logger.info(f"Derived project_id='{args.project_id}' from folder name")

        # Attempt to derive speaker from any monologue JSON file if not provided
        if not args.speaker_name:
            try:
                for f in project_path.glob("*.json"):
                    parts = f.stem.split('-')
                    if len(parts) >= 3 and parts[-2] == 'monologue':
                        args.speaker_name = parts[-3]
                        logger.info(f"Derived speaker_name='{args.speaker_name}' from {f.name}")
                        break
            except Exception:
                pass
        if not args.speaker_name and not (args.edit_image or args.image_only or args.img2vid_silent):
            logger.error("Unable to determine --speaker-name; please specify explicitly.")
            return 1
    else:
        timestamp = datetime.now().strftime("%d%m%y-%H%M%S")
        project_folder_name = f"{args.project_id}--{timestamp}"
        project_path = Path("./media") / project_folder_name
        project_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Project folder created at: {project_path}")

    # Ensure sanitized identifiers are available (works for both existing and new folders)
    sanitized_project_id = args.project_id.replace(' ', '-')
    sanitized_speaker_name = (args.speaker_name or 'Speaker').replace(' ', '-')

    # Prepare TTS output directory (will be used later if requested)
    tts_output_dir = project_path / "tts"
    # Directory will be created on demand later

    # Define expected monologue file paths
    base_filename = f"{sanitized_project_id}-{sanitized_speaker_name}-monologue-{args.script_number}"
    json_monologue_path = project_path / f"{base_filename}.json"

    # Keep a global list so later steps (e.g. lipsync) can access generated audio
    tts_files: list[str] = []
    lipsync_results = []

    # 0. IMAGE EDITING ONLY MODE – run and exit before monologue steps
    if args.edit_image or args.image_only:
        images_dir = project_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        if not args.subject_image_url or not args.image_prompt:
            logger.error("When --edit-image or --edit-image-only is set, both --subject-image-url and --image-prompt must be provided.")
            return 1

        subject_url = make_space_url_accessible(args.subject_image_url)
        background_url = make_space_url_accessible(args.background_image_url) if args.background_image_url else None

        api_username = args.username or os.environ.get("API_USERNAME")
        api_password = args.password or os.environ.get("API_PASSWORD")
        if not api_username or not api_password:
            logger.error("API_USERNAME and API_PASSWORD must be provided via CLI or env for image editing.")
            return 1

        before_files = set(images_dir.glob('*'))

        if background_url:
            script_path = "scripts/podcast_generation/edit_image_kontext_multi_list.py"
            cmd = [
                sys.executable, script_path,
                "--subject_image_url", subject_url,
                "--background_image_url", background_url,
                "--prompt", args.image_prompt,
                "--aspect_ratio", args.image_aspect_ratio,
                "--output_format", args.image_output_format,
                "--output_dir", str(images_dir),
                "--api_base_url", args.api_base_url,
                "--username", api_username, "--password", api_password,
            ]
        else:
            script_path = "scripts/podcast_generation/edit_image_kontext_pro.py"
            cmd = [
                sys.executable, script_path,
                "--subject_image_url", subject_url,
                "--prompt", args.image_prompt,
                "--aspect_ratio", args.image_aspect_ratio,
                "--output_format", args.image_output_format,
                "--output_dir", str(images_dir),
                "--api_base_url", args.api_base_url,
                "--username", api_username, "--password", api_password,
            ]

        if args.image_seed is not None:
            cmd.extend(["--seed", str(args.image_seed)])
        if args.image_safety_tolerance is not None:
            cmd.extend(["--safety_tolerance", str(args.image_safety_tolerance)])

        stdout_str, rc = run_subprocess_stream(cmd)
        if rc != 0:
            logger.error("Image editing subprocess failed.")
            return 1

        import urllib.parse
        new_files = set(images_dir.glob('*')) - before_files

        # Build background slug for naming
        if args.background_image_url:
            path_part = urllib.parse.urlparse(args.background_image_url).path
            background_slug = Path(path_part).stem.replace(' ', '-').replace('_', '-') or 'background'
        else:
            background_slug = 'subject'

        for f in new_files:
            # Build target filename
            ext = f.suffix
            target_name = f"{project_folder_name}-{sanitized_speaker_name}-{background_slug}{ext}"
            target_path = images_dir / target_name
            try:
                f.rename(target_path)
                logger.info(f"Renamed image file to: {target_path}")
            except Exception as e:
                logger.warning(f"Could not rename {f} to {target_name}: {e}")

        logger.info("Image editing step complete.")

        # -----------------------------------------
        # 1.5 VIDEO GENERATION (optional)
        # -----------------------------------------
        if args.img2vid_silent:
            logger.info("Starting video generation pipeline (Kling 1.6 Pro)...")

            if not args.subject_image_url:
                logger.error("--subject-image-url must be provided when --img2vid-silent is set.")
                return 1

            api_username = args.username or os.environ.get("API_USERNAME") or os.environ.get("DJANGO_SUPERUSER_USERNAME")
            api_password = args.password or os.environ.get("API_PASSWORD") or os.environ.get("DJANGO_SUPERUSER_PASSWORD")
            if not api_username or not api_password:
                logger.error("API credentials are required for video generation.")
                return 1

            # If the user passed the path to an existing "video" directory, use it directly.
            if project_path.name.lower() == "video":
                videos_dir = project_path
            else:
                videos_dir = project_path / "video"
                videos_dir.mkdir(parents=True, exist_ok=True)

            cmd_video = [
                sys.executable,
                "scripts/podcast_generation/subject_image_to_podcast_video i2v.py",
                "--image-url", make_space_url_accessible(args.subject_image_url),
                "--video-prompt", args.video_prompt,
                "--api-base", args.api_base_url,
                "--username", api_username,
                "--password", api_password,
                "--local-storage-path", str(videos_dir)
            ]
            stdout_str, rc = run_subprocess_stream(cmd_video)

            if rc != 0:
                logger.error("Video generation subprocess failed.")
                return 1

            # Rename the summary JSON for consistency
            pv_json = project_path / "podcast_video_output.json"
            if pv_json.exists():
                target_json = project_path / f"{project_folder_name}-{sanitized_speaker_name}-silent-video.json"
                try:
                    pv_json.rename(target_json)
                    logger.info(f"Video generation summary saved to {target_json}")
                except Exception as e:
                    logger.warning(f"Could not rename video output JSON: {e}")
            else:
                logger.warning("Expected podcast_video_output.json not found; skipping rename step.")

        # If the user requested only the image pipeline, exit early now
        if args.image_only:
            return 0

    # -------------------------------------------------
    # 0A. IMAGE → VIDEO ONLY MODE (silent) – early exit
    # -------------------------------------------------
    if args.img2vid_silent and not (args.edit_image or args.image_only):
        logger.info("Running image-to-video (silent) pipeline only – skipping all other steps.")

        if not args.subject_image_url:
            logger.error("--subject-image-url must be provided when --img2vid-silent is set.")
            return 1

        api_username = args.username or os.environ.get("API_USERNAME") or os.environ.get("DJANGO_SUPERUSER_USERNAME")
        api_password = args.password or os.environ.get("API_PASSWORD") or os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not api_username or not api_password:
            logger.error("API credentials are required for video generation.")
            return 1

        # If the user passed the path to an existing "video" directory, use it directly.
        if project_path.name.lower() == "video":
            videos_dir = project_path
        else:
            videos_dir = project_path / "video"
            videos_dir.mkdir(parents=True, exist_ok=True)

        cmd_video = [
            sys.executable,
            "scripts/podcast_generation/subject_image_to_podcast_video i2v.py",
            "--image-url", make_space_url_accessible(args.subject_image_url),
            "--video-prompt", args.video_prompt,
            "--api-base", args.api_base_url,
            "--username", api_username,
            "--password", api_password,
            "--local-storage-path", str(videos_dir)
        ]
        stdout_str, rc = run_subprocess_stream(cmd_video)

        if rc != 0:
            logger.error("Video generation subprocess failed.")
            return 1

        # Rename the summary JSON for consistency
        pv_json = project_path / "podcast_video_output.json"
        if pv_json.exists():
            target_json = project_path / f"{project_folder_name}-{sanitized_speaker_name}-silent-video.json"
            try:
                pv_json.rename(target_json)
                logger.info(f"Video generation summary saved to {target_json}")
            except Exception as e:
                logger.warning(f"Could not rename video output JSON: {e}")
        else:
            logger.warning("Expected podcast_video_output.json not found; skipping rename step.")

        # Completed the requested action; exit early
        return 0

    # 2. Generate monologue script if it doesn't exist
    if not json_monologue_path.exists():
        if not args.prompt:
            logger.error("--prompt is required to generate a new monologue script (or provide an existing project folder containing the JSON).")
            return 1
        logger.info("Monologue JSON not found. Generating script...")
        # Prepare arguments for the script generation subprocess
        script_args = [
            sys.executable,
            "scripts/podcast_generation/generate_monologue_script.py",
            "--project-name", args.project_id,
            "--prompt", args.prompt,
            "--speaker-name", args.speaker_name,
            "--save-location", str(project_path),
            "--script-number", str(args.script_number)
        ]

        # Handle optional PDF
        if args.pdf_url:
            pdf_path = download_pdf(make_space_url_accessible(args.pdf_url), project_path)
            if pdf_path:
                script_args.extend(["--pdf-file", str(pdf_path)])

        # Run the script generation
        stdout_str, rc = run_subprocess_stream(script_args)
        if rc != 0:
            logger.error("Monologue generation script returned non-zero exit code")
            return 1
        logger.info("Monologue script generated successfully.")
    else:
        logger.info("Monologue JSON already exists. Skipping script generation.")

    # 3. Upload generated files to DigitalOcean Spaces if requested
    if args.upload_to_do:
        bucket_name = os.environ.get("DO_SPACES_BUCKET")
        if not bucket_name:
            logger.error("Error: DO_SPACES_BUCKET environment variable is not set.")
            return 1

        logger.info(f"Uploading generated files to DO Spaces bucket: {bucket_name}")
        uploaded_urls = {}

        for file_path in project_path.iterdir():
            if file_path.is_file() and file_path.name.endswith(('.txt', '.json')):
                object_name = f"{project_folder_name}/{file_path.name}"
                url = upload_file_to_do_spaces(file_path, bucket_name, object_name)
                if url:
                    uploaded_urls[file_path.name] = url
        
        if uploaded_urls:
            logger.info("All files uploaded successfully.")
            print(json.dumps(uploaded_urls, indent=2))
        else:
            logger.warning("No files were uploaded.")

    # Make voice_id available in wider scope so TTS step can reuse it
    voice_id = args.voice_id

    # -----------------------------------------
    # 4. Voice Clone Generation (optional)
    # -----------------------------------------
    if args.generate_voice_clone:
        logger.info("Starting voice cloning workflow...")
        if not voice_id:
            logger.info("No Voice ID provided. Attempting to create a new voice clone.")
            if not args.sample_audio_url:
                logger.error("Error: --sample-audio-url is required for voice cloning.")
                return 1

            api_username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
            api_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
            if not api_username or not api_password:
                logger.error("Error: DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD must be set in the environment.")
                return 1

            base_filename_vc = f"{project_folder_name}-voice-clone-{sanitized_speaker_name}"
            clone_script_args = [
                sys.executable,
                "scripts/podcast_generation/create_voice_clone_minimax.py",
                "--voice-file", args.sample_audio_url,
                "--speaker-name", args.speaker_name,
                "--base-filename", base_filename_vc,
                "--output-dir", str(project_path),
                "--username", api_username,
                "--password", api_password,
            ]

            logger.info("Running voice cloning subprocess...")
            stdout_str, rc = run_subprocess_stream(clone_script_args)

            # Attempt to parse the last JSON line from collected stdout
            vc_info = None
            for line in reversed(stdout_str.splitlines()):
                try:
                    obj = json.loads(line)
                    if "voice_id" in obj and "json_path" in obj:
                        vc_info = obj
                        break
                except json.JSONDecodeError:
                    continue

            if rc != 0 or not vc_info:
                logger.error("Voice clone script did not complete successfully or returned invalid data.")
                return 1

            voice_id = vc_info["voice_id"]
            vc_json_path = Path(vc_info["json_path"])
            logger.info(f"Voice clone created. Voice ID: {voice_id}; JSON: {vc_json_path}")

            # Merge/append project metadata into the JSON file
            try:
                data = json.loads(vc_json_path.read_text())
                data.update({"project_folder": project_folder_name, "speaker_name": args.speaker_name})
                vc_json_path.write_text(json.dumps(data, indent=2))
            except Exception as e:
                logger.warning(f"Failed to augment voice clone JSON: {e}")
    else:
        logger.info("--generate-voice-clone flag not provided; skipping clone step.")

    # -----------------------------------------
    # 5. TTS Generation (optional)
    # -----------------------------------------
    if args.generate_TTS:
        if not voice_id:
            logger.error("TTS generation requested but no voice_id is available. Provide --voice-id or enable --generate-voice-clone.")
            return 1

        # Load the monologue JSON
        if not json_monologue_path.exists():
            logger.error(f"Monologue JSON not found at {json_monologue_path}; cannot generate TTS.")
            return 1

        try:
            monologue_data = json.loads(json_monologue_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load monologue JSON: {e}")
            return 1

        if not isinstance(monologue_data, list):
            logger.error("Monologue JSON is not a list; unexpected format.")
            return 1

        # Ensure TTS directory
        tts_output_dir.mkdir(parents=True, exist_ok=True)

        api_username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        api_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not api_username or not api_password:
            logger.error("Error: DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD must be set in the environment for TTS generation.")
            return 1

        for idx, item in enumerate(monologue_data, 1):
            # Attempt to extract sentence text from known keys or treat the item as plain string
            if isinstance(item, dict):
                sentence_text = item.get("sentence") or item.get("text") or item.get("line") or ""
            else:
                sentence_text = str(item)

            if not sentence_text.strip():
                logger.warning(f"Skipping empty sentence at index {idx}")
                continue

            logger.info(f"Generating TTS for sentence {idx}/{len(monologue_data)}: {sentence_text[:60]}...")

            before_files = set(tts_output_dir.glob('*'))

            tts_args = [
                sys.executable,
                "scripts/podcast_generation/generate_voice_minimax_speech2hd.py",
                "--text", sentence_text,
                "--voice_id", voice_id,
                "--speaker_name", args.speaker_name,
                "--output_dir", str(tts_output_dir),
                "--model", args.tts_model,
                "--api_base_url", args.api_base_url,
                "--username", api_username,
                "--password", api_password,
            ]

            stdout_str, rc = run_subprocess_stream(tts_args)
            if rc != 0:
                logger.error(f"TTS subprocess failed for sentence {idx}")
                return 1

            # Detect newly created file
            new_files = set(tts_output_dir.glob('*')) - before_files
            if len(new_files) != 1:
                logger.error(f"Could not uniquely determine output audio file for sentence {idx}")
                return 1

            generated_file = new_files.pop()

            # Rename to desired convention
            new_name = f"{project_folder_name}-{sanitized_speaker_name}-{voice_id}-TTS-{idx}{generated_file.suffix}"
            target_path = tts_output_dir / new_name
            generated_file.rename(target_path)
            logger.info(f"Saved TTS audio to {target_path}")
            tts_files.append(str(target_path))

        # Save a summary JSON of generated TTS files
        summary_path = project_path / f"{project_folder_name}-{sanitized_speaker_name}-{voice_id}-TTS.json"
        summary_path.write_text(json.dumps({"audio_files": tts_files}, indent=2))
        logger.info(f"TTS generation complete. Summary written to {summary_path}")
    else:
        logger.info("Skipping TTS generation (use --generate-TTS to enable).")

    # -----------------------------------------
    # 6. OPTIONAL: Create lipsync videos
    # -----------------------------------------
    if args.generate_lipsync:
        # Determine which audio files to use
        if args.audio_dir:
            audio_dir = Path(args.audio_dir).expanduser().resolve()
            if not audio_dir.is_dir():
                logger.error(f"--audio-dir {audio_dir} is not a directory")
                return 1
            audio_paths = sorted([p for p in audio_dir.iterdir() if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.aac')])
            if not audio_paths:
                logger.error(f"No supported audio files found in {audio_dir}")
                return 1
        else:
            audio_paths = tts_files
        if not audio_paths:
            logger.error("No audio files available for lipsync generation.")
            return 1

        silent_json_path = project_path / f"{project_folder_name}-{sanitized_speaker_name}--i2v-silent.json"
        if not silent_json_path.exists():
            logger.error(f"Silent-video JSON not found at {silent_json_path}; cannot run lipsync.")
            return 1
        try:
            silent_data = json.loads(silent_json_path.read_text())
            silent_video_url = silent_data.get("video") or silent_data.get("video_url")
            if not silent_video_url:
                raise ValueError("video_url missing in silent-video JSON")
        except Exception as e:
            logger.error(f"Failed to read silent-video JSON: {e}")
            return 1

        api_user = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        api_pass = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not (api_user and api_pass):
            logger.error("API credentials required for lipsync generation.")
            return 1

        lipsync_dir = project_path / "lipsync"
        lipsync_dir.mkdir(parents=True, exist_ok=True)

        for idx, audio_path in enumerate(audio_paths, 1):
            output_mp4 = lipsync_dir / f"{project_folder_name}-{sanitized_speaker_name}-lipsync-{idx}.mp4"
            cmd_ls = [
                sys.executable,
                "scripts/podcast_generation/lipsync-video-generator-kling.py",
                "--video-url", silent_video_url,
                "--audio-file", str(audio_path),
                "--api-base", args.api_base_url,
                "--username", api_user,
                "--password", api_pass,
                "--output-path", str(output_mp4)
            ]
            stdout_str, rc = run_subprocess_stream(cmd_ls)
            if rc != 0:
                logger.error(f"Lipsync subprocess failed for {audio_path}")
                return 1
            generic_json = Path("lipsync_output.json")
            clip_json_path = lipsync_dir / f"{project_folder_name}-{sanitized_speaker_name}-lipsync-{idx}.json"
            if generic_json.exists():
                try:
                    generic_json.rename(clip_json_path)
                except Exception as e:
                    logger.warning(f"Could not rename lipsync JSON: {e}")
            lipsync_results.append({"audio": str(audio_path), "video": str(output_mp4), "json": str(clip_json_path)})

        # Aggregate summary
        summary_json = project_path / f"{project_folder_name}-{sanitized_speaker_name}-lipsync.json"
        summary_json.write_text(json.dumps({"clips": lipsync_results}, indent=2))
        logger.info(f"Lipsync generation complete. Summary written to {summary_json}")

        # Merge all generated lipsync videos into a single final video
        try:
            lipsync_mp4s = sorted(lipsync_dir.glob("*.mp4"))
            if lipsync_mp4s:
                # Use the extension of the first clip for the merged file
                ext = lipsync_mp4s[0].suffix
                final_video_path = project_path / f"{project_folder_name}{ext}"
                merge_videos([str(p) for p in lipsync_mp4s], final_video_path)
                logger.info(f"Final merged video saved to {final_video_path}")
            else:
                logger.warning("No lipsync MP4 files found to merge.")
        except Exception as e:
            logger.error(f"Failed to merge lipsync videos: {e}")
    else:
        logger.info("Skipping lipsync generation (use --generate-lipsync to enable).")

    logger.info(f"Monologue generation process complete for project {args.project_id}.")
    logger.info(f"Output files are in: {project_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
# https://aicc.nyc3.cdn.digitaloceanspaces.com/avatars/austin/video/tmp4ix5quta.mp4