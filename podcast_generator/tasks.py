import os
import json
import logging
import requests
import datetime
import uuid
from pathlib import Path
import subprocess
import shlex
import sys
import tempfile
import re
from celery import Celery, group, chord
from celery.signals import setup_logging
from dotenv import load_dotenv
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from podcast_generator.models import PodcastGenerationJob, PodcastDialogue
from audio_generation.models import MinimaxSpeechJob
from video_generation.models import KlingVideoJob, KlingLipsyncJob
from video_generation.tasks import generate_kling_lipsync, generate_kling_video
from podcast_generator.services import PodcastJobService
from pydantic import ValidationError
from shared.clients.storage_client import storage_client

# Webhook helpers
from shared.utils.webhook_utils import generate_webhook_secret, generate_webhook_url

# JSON schema validation helper
from podcast_generator.validators import validate_script_json

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
root_logger = logging.getLogger()  # Root logger for broader capture in tests

# Load environment variables
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', './media/output')

# Create Celery app
app = Celery('podcast_generator')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Create output directory if it doesn't exist
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Utility: task-level logging decorator must be defined *before* it is referenced
# -----------------------------------------------------------------------------

def with_task_logging(func):
    """Decorator that adds structured logging to Celery task execution.

    It logs a message when the task starts, when it finishes successfully, and
    when it raises an exception. Declared early so that decorators applied
    further down in this file are resolved correctly at import time.
    """

    def wrapper(*args, **kwargs):
        task_self = args[0] if args else None
        task_name = getattr(task_self, "name", func.__name__)
        logger.info("Starting task %s", task_name)
        root_logger.info("Starting task %s", task_name)
        try:
            result = func(*args, **kwargs)
            logger.info("Task %s completed successfully", task_name)
            root_logger.info("Task %s completed successfully", task_name)
            return result
        except Exception as exc:
            logger.error("Task %s failed: %s", task_name, exc)
            root_logger.error("Task %s failed: %s", task_name, exc)
            raise

    return wrapper

# -----------------------------------------------------------------------------
# PIPELINE ORCHESTRATION – replaces the old dummy task
# ----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, retry_backoff=True, name="podcast_generator.tasks.process_podcast_generation")
@with_task_logging
def process_podcast_generation(self, job_id):
    """Entry-point: delegate to PodcastJobService.start_pipeline"""
    service = PodcastJobService.for_id(job_id)
    return service.start_pipeline()

# -----------------------------------------------------------------------------
# 0) DOCUMENT INGESTION / PDF EXTRACTION
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, retry_backoff=True, name="podcast_generator.tasks.ingest_document_for_job")
@with_task_logging
def ingest_document_for_job(self, job_id):
    """Download a remote PDF and populate ``document_content``.

    After extraction, the task automatically fires ``generate_script_for_job`` so
    the pipeline continues. If no ``document_source_url`` is set, it skips
    ingestion and directly launches script generation.
    """
    try:
        job = PodcastGenerationJob.objects.get(id=job_id)

        if not job.document_source_url:
            logger.info("Job %s: document_source_url not set – skipping ingestion", job_id)
            generate_script_for_job.delay(str(job_id))
            return

        logger.info("Job %s: downloading document from %s", job_id, job.document_source_url)

        # ------------------------------------------------------------------
        # 1) Download PDF (or other doc type)
        # ------------------------------------------------------------------
        response = requests.get(job.document_source_url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # ------------------------------------------------------------------
        # 2) Extract text (best-effort)
        # ------------------------------------------------------------------
        extracted_text = ""
        try:
            import pdfplumber  # Lazy import to keep global deps optional

            with pdfplumber.open(tmp_path) as pdf:
                extracted_text = "\n".join(
                    (page.extract_text() or "") for page in pdf.pages
                )
        except Exception as exc:
            logger.warning("Job %s: failed to parse PDF – %s", job_id, exc)

        # ------------------------------------------------------------------
        # 3) Persist and continue pipeline
        # ------------------------------------------------------------------
        job.document_content = extracted_text
        job.save(update_fields=["document_content"])

        logger.info("Job %s: document ingestion completed (chars=%s)", job_id, len(extracted_text))

        # Proceed to script generation
        generate_script_for_job.delay(str(job_id))

    except PodcastGenerationJob.DoesNotExist:
        logger.error("Job %s not found while ingesting document", job_id)
    except Exception as exc:
        logger.error("Document ingestion failed for job %s: %s", job_id, exc)
        raise self.retry(exc=exc)

# -----------------------------------------------------------------------------
# 1) SCRIPT GENERATION
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, retry_backoff=True, name="podcast_generator.tasks.generate_script_for_job")
@with_task_logging
def generate_script_for_job(self, job_id):
    """Generate script with utility scripts, create Dialogue rows, move to audio stage."""
    try:
        with transaction.atomic():
            job = PodcastGenerationJob.objects.select_for_update().get(id=job_id)
            topic = job.podcast_idea
            speaker_count = job.speaker_count
            speaker_names = [n for n in [job.speaker1_name, job.speaker2_name] if n]

            # Determine CLI-style project folder and script subdir
            project_path = ensure_project_folder(job)

            scripts_dir = Path(__file__).resolve().parent.parent / 'scripts'
            scripts_output_dir = project_path / "scripts"
            scripts_output_dir.mkdir(parents=True, exist_ok=True)

            if speaker_count == 1:
                # --- Monologue ---------------------------------------------------
                script_path = scripts_dir / 'generate_monologue_script.py'

                cmd = [
                    sys.executable,
                    str(script_path),
                    '--prompt', topic,
                    '--speaker_name', speaker_names[0],
                    '--output_dir', str(scripts_output_dir),
                ]

                base_name = topic.lower().replace(" ", "_")[:20]
                output_file = scripts_output_dir / f"{base_name}_monologue.json"
            else:
                # --- Dialogue ----------------------------------------------------
                script_path = scripts_dir / 'generate_dialogue_script.py'

                speaker_ids = [job.speaker1_voice_id or "spk_1", job.speaker2_voice_id or "spk_2"]

                cmd = [
                    sys.executable,
                    str(script_path),
                    '--prompt', topic,
                    '--speaker_names', *speaker_names,
                    '--speaker_ids', *speaker_ids,
                    '--output_dir', str(scripts_output_dir),
                ]

                base_name = topic.lower().replace(" ", "_")[:20]
                output_file = scripts_output_dir / f"{base_name}_dialogue.json"

            # Execute the script
            logger.info(f"Running script: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Script output: {result.stdout}")

            # Process the generated script
            with open(output_file, "r") as f:
                script_data = json.load(f)

            # Persist full script JSON for later reference --------------------
            job.script = script_data
            job.save(update_fields=["script"])

            # Validate & normalise JSON --------------------------------------
            try:
                lines = validate_script_json(script_data)
            except ValidationError as exc:
                # Mark job as failed and abort pipeline
                service = PodcastJobService.for_id(job_id)
                service.transition(
                    "failed",
                    error_message=f"Invalid script JSON produced by generator: {exc}",
                )
                return

            # Persist Dialogue rows -----------------------------------------
            for i, line in enumerate(lines):
                speaker_name = line.speaker
                dialogue_text = line.text
                emotion = line.emotion

                # Resolve voice ID from job configuration
                if speaker_name == job.speaker1_name:
                    voice_id = job.speaker1_voice_id
                elif speaker_name == job.speaker2_name:
                    voice_id = job.speaker2_voice_id
                else:
                    voice_id = None  # fallback – will be handled later

                PodcastDialogue.objects.create(
                    podcast_job=job,
                    speaker_name=speaker_name,
                    speaker_voice_id=voice_id or "",  # model requires non-null
                    sequence_number=i + 1,
                    dialogue_text=dialogue_text,
                    emotion=emotion,
                )

        # Kick off audio stage ---------------------------------------------------
        service = PodcastJobService.for_id(job_id)
        service.transition('audio_pending')

        # If this job is configured to skip audio (rare for monologue, but
        # supported for full CLI parity), jump directly to the next stage
        # depending on other skip flags.
        if job.skip_audio:
            if job.skip_video or job.skip_lipsync:
                service.transition('completed')
            else:
                service.transition('video_pending')
                generate_video_for_speakers.delay(job_id)
            return

        # Enqueue TTS generation for each dialogue
        enqueue_audio_for_all_dialogues.delay(job_id)

    except PodcastGenerationJob.DoesNotExist:
        logger.error(f"Job {job_id} not found during script generation.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Script generation failed for job {job_id}: {e.stderr}")
        service = PodcastJobService.for_id(job_id)
        service.transition('failed', error_message=f"Script generation failed: {e.stderr}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_script_for_job for job {job_id}: {e}")
        service = PodcastJobService.for_id(job_id)
        service.transition('failed', error_message=str(e))
        raise self.retry(exc=e)

# -----------------------------------------------------------------------------
# Helper – ensure a deterministic project folder that mirrors CLI convention
# -----------------------------------------------------------------------------

def ensure_project_folder(job: PodcastGenerationJob) -> Path:
    """Return Path to the on-disk project folder, creating it if necessary.

    Naming convention mirrors the standalone CLI:
        <project-id>--<ddmmyy>-<hhmmss>
    where *project-id* is the job's UUID (first 8 chars for brevity).
    The folder lives under global ``OUTPUT_DIR``.
    The relative folder name is stored back to ``job.media_folder`` so
    downstream tasks (possibly on other workers) can derive the same path.
    """

    if job.media_folder and job.media_folder.startswith(f"{job.id}"):
        project_name = job.media_folder  # already in desired format
    else:
        timestamp = timezone.localtime().strftime("%d%m%y-%H%M%S")
        project_name = f"{str(job.id)[:8]}--{timestamp}"
        job.media_folder = project_name
        job.save(update_fields=["media_folder"])

    project_path = Path(OUTPUT_DIR) / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    return project_path

# -----------------------------------------------------------------------------
# Small helper – safe filename
# -----------------------------------------------------------------------------

def sanitize_for_filename(value: str) -> str:
    """Return a filesystem-safe version of *value* (lowercase, no spaces)."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).lower()

# -----------------------------------------------------------------------------
# 2) AUDIO GENERATION (VOICE + TTS)
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=10, default_retry_delay=30, name="podcast_generator.tasks.enqueue_audio_for_all_dialogues")
@with_task_logging
def enqueue_audio_for_all_dialogues(self, job_id: str):
    """
    Enqueues TTS generation tasks for all dialogue entries of a given podcast job.
    Assumes voice IDs are already present in the job model.
    """
    try:
        job = PodcastGenerationJob.objects.get(id=job_id)
        dialogues = job.dialogues.all()
        logger.info("Job %s: Enqueuing audio generation for %s dialogues.", job.id, dialogues.count())

        project_path = ensure_project_folder(job)
        audio_dir = project_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        project_base = project_path.name  # e.g. <jobid>--<date>

        # Map speaker → voice ID
        speaker_to_voice_id = {job.speaker1_name: job.speaker1_voice_id}
        if job.speaker_count == 2:
            speaker_to_voice_id[job.speaker2_name] = job.speaker2_voice_id

        for dialogue in dialogues:
            voice_id = speaker_to_voice_id.get(dialogue.speaker_name)

            if not voice_id:
                logger.warning(
                    "Skipping dialogue %s: no voice_id found for speaker '%s' in job %s",
                    dialogue.id,
                    dialogue.speaker_name,
                    job_id,
                )
                continue

            sanitized_speaker = sanitize_for_filename(dialogue.speaker_name)
            audio_output_path = audio_dir / f"{project_base}-{sanitized_speaker}-tts-{dialogue.sequence_number}.wav"

            generate_tts_for_dialogue.delay(
                dialogue_id=str(dialogue.id),
                voice_id=voice_id,
                text=dialogue.dialogue_text,
                output_path=str(audio_output_path),
            )

        check_audio_completion.apply_async(args=[job_id], countdown=30)

    except PodcastGenerationJob.DoesNotExist:
        logger.error(f"Job with id {job_id} not found.")
    except Exception as e:
        logger.error(f"Error in enqueue_audio_for_all_dialogues for job {job_id}: {e}")
        self.retry(exc=e, countdown=30, max_retries=3)


@app.task(bind=True, max_retries=3, name="podcast_generator.tasks.generate_tts_for_dialogue")
@with_task_logging
def generate_tts_for_dialogue(self, dialogue_id: str, voice_id: str, text: str, output_path: str):
    """
    Generates TTS for a single dialogue segment and saves it to a file.
    """
    try:
        dialogue = PodcastDialogue.objects.get(id=dialogue_id)
        logger.info(f"Starting TTS for dialogue {dialogue_id} for job {dialogue.podcast_job.id} -> {output_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # PRODUCTION PATH: Reuse the central Minimax speech generation pipeline
        # defined in `audio_generation.tasks.generate_minimax_speech`.
        #
        # 1. Create a `MinimaxSpeechJob` row containing the text and voice ID.
        # 2. Execute the Minimax speech task *synchronously* with `.apply(...)` so
        #    this Celery worker blocks until the audio is ready.  When
        #    `webhook_url` is `None`, that task already waits for the Replicate
        #    prediction to finish, so we can rely on the output URL afterwards.
        # 3. Persist the returned `output_url` onto the `PodcastDialogue` row so
        #    downstream stages detect completion.
        # ------------------------------------------------------------------

        # Step 1 – create job (all optional params rely on model defaults)
        speech_job = MinimaxSpeechJob.objects.create(
            text=text,
            voice_id=voice_id,
            model_version="turbo",  # fast and good enough; change if needed
        )

        # Step 2 – run generation synchronously (no webhook)
        generate_minimax_speech.apply(args=[str(speech_job.id)])

        # Reload to obtain output URL set by the audio task
        speech_job.refresh_from_db()

        if not speech_job.output_url:
            raise ValueError(
                f"Minimax speech job {speech_job.id} completed without output_url"
            )

        # Step 3 – optionally download the audio file locally -----------------
        if output_path:
            try:
                resp = requests.get(speech_job.output_url, timeout=120)
                resp.raise_for_status()
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as fh:
                    fh.write(resp.content)
            except Exception as dl_exc:
                logger.warning("Could not download audio for dialogue %s to %s: %s", dialogue_id, output_path, dl_exc)

        # Store the URL on the dialogue --------------------------------------
        dialogue.audio_url = speech_job.output_url
        dialogue.save(update_fields=["audio_url"])

        logger.info("TTS for dialogue %s completed. Audio URL=%s", dialogue_id, dialogue.audio_url)

    except PodcastDialogue.DoesNotExist:
        logger.error(f"Dialogue with id {dialogue_id} not found.")
    except Exception as e:
        logger.error(f"Error in generate_tts_for_dialogue for dialogue {dialogue_id}: {e}")
        self.retry(exc=e, countdown=30, max_retries=3)


@app.task(bind=True, max_retries=20, default_retry_delay=30, name="podcast_generator.tasks.check_audio_completion")
@with_task_logging
def check_audio_completion(self, job_id):
    """Poll until all dialogue rows have audio_url present → proceed to video stage."""
    service = PodcastJobService.for_id(job_id)
    job = service.job

    if job.dialogues.filter(audio_url__isnull=True).exists():
        logger.info(f"Job {job_id}: Waiting for audio generation to complete. Retrying...")
        raise self.retry()

    logger.info(f"Job {job_id}: All audio generated.")

    if service.job.skip_video:
        if service.job.skip_lipsync:
            service.transition('completed')
        else:
            logger.info("Job %s: skip_video=True but lipsync requested – cannot proceed. Marking failed.", job_id)
            service.transition('failed', error_message='Invalid skip flag combination')
        return

    service.transition('video_pending')

    # Audio side finished – attempt to move to lipsync if videos are also ready
    try_start_lipsync.delay(job_id)

# -----------------------------------------------------------------------------
# 3) VIDEO GENERATION
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, retry_backoff=True, name="podcast_generator.tasks.generate_video_for_speakers")
@with_task_logging
def generate_video_for_speakers(self, job_id):
    """Create speaker videos *in parallel* and trigger lipsync once all are done."""
    service = PodcastJobService.for_id(job_id)
    job = service.job

    try:
        if job.skip_video:
            logger.info("Job %s: skip_video=True – skipping video generation", job_id)
            return

        tasks_to_run = []
        if job.speaker1_name:
            tasks_to_run.append(generate_video_for_speaker.s(job_id, 1))
        if job.speaker_count == 2 and job.speaker2_name:
            tasks_to_run.append(generate_video_for_speaker.s(job_id, 2))

        if not tasks_to_run:
            logger.warning("No speaker video tasks generated for job %s", job_id)
            service.transition('failed', error_message='No speakers configured for video generation.')
            return

        # Mark that videos are being processed
        service.transition('video_processing')

        # Launch the group and, when complete, try to start lipsync
        chord(tasks_to_run)(try_start_lipsync.s(job_id))

    except Exception as e:
        logger.error("Failed to enqueue video generation for job %s: %s", job_id, e)
        service.transition('failed', error_message=str(e))
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3, name="podcast_generator.tasks.generate_video_for_speaker")
@with_task_logging
def generate_video_for_speaker(self, job_id: str, speaker_number: int):
    """Generates a video for a single speaker using an external script."""
    service = PodcastJobService.for_id(job_id)
    job = service.job

    try:
        if job.skip_video:
            logger.info("Job %s: skip_video=True – skipping video generation for speaker %s", job_id, speaker_number)
            return

        speaker_name = job.speaker1_name if speaker_number == 1 else job.speaker2_name
        speaker_image = job.speaker1_image if speaker_number == 1 else job.speaker2_image

        if not speaker_image:
            logger.warning(f"No image found for speaker {speaker_number} in job {job_id}. Skipping video generation.")
            return

        project_path = ensure_project_folder(job)
        video_dir = project_path / "video"
        video_dir.mkdir(parents=True, exist_ok=True)

        project_base = project_path.name
        sanitized_speaker = sanitize_for_filename(speaker_name)
        output_path = video_dir / f"{project_base}-{sanitized_speaker}-i2v-silent.mp4"

        scripts_dir = Path(__file__).resolve().parent.parent / 'scripts'
        script_path = scripts_dir / 'subject_image_to_podcast_video_i2v.py'

        cmd = [
            sys.executable, str(script_path),
            '--image-url', speaker_image,
            '--output-path', str(output_path)
        ]

        logger.info(f"Running video generation for speaker {speaker_number}: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        upload_data = storage_client.upload_file(
            str(output_path),
            endpoint_type='video_generation',
            include_presigned=True,
        )

        # Handle return type (str or dict)
        if isinstance(upload_data, dict):
            public_url = upload_data.get("public_url") or upload_data.get("url")
            presigned = upload_data.get("presigned_url")
        else:
            public_url = upload_data
            presigned = None

        if speaker_number == 1:
            job.speaker1_video_url = public_url
            job.speaker1_video_presigned_url = presigned
        else:
            job.speaker2_video_url = public_url
            job.speaker2_video_presigned_url = presigned
        job.save(update_fields=[
            "speaker1_video_url" if speaker_number == 1 else "speaker2_video_url",
            "speaker1_video_presigned_url" if speaker_number == 1 else "speaker2_video_presigned_url",
        ])

    except Exception as e:
        logger.error(f"Video generation failed for speaker {speaker_number}, job {job_id}: {e}")
        # We don't fail the whole job, but we could add more specific error handling
        raise self.retry(exc=e)

# -----------------------------------------------------------------------------
# 4) LIPSYNC
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, retry_backoff=True, name="podcast_generator.tasks.enqueue_lipsync_for_dialogues")
@with_task_logging
def enqueue_lipsync_for_dialogues(self, job_id):
    """Iterate over all dialogues and launch lipsync tasks where needed."""
    service = PodcastJobService.for_id(job_id)
    job = service.job

    try:
        dialogues_to_process = job.dialogues.filter(lipsync_url__isnull=True)
        lipsync_tasks = [process_lipsync_for_dialogue.s(d.id) for d in dialogues_to_process]

        if lipsync_tasks:
            group(lipsync_tasks).apply_async()
            check_lipsync_completion.apply_async((job_id,), countdown=60)
        else:
            # All dialogues already have lipsync videos, move to final combination
            combine_podcast_video.delay(job_id)

    except Exception as e:
        logger.error(f"Failed to enqueue lipsync for job {job_id}: {e}")
        service.transition('failed', error_message=str(e))
        raise self.retry(exc=e)

# Helper / internal tasks for lipsync processing --------------------------------

@app.task(bind=True, max_retries=5, default_retry_delay=30, name="podcast_generator.tasks.process_lipsync_for_dialogue")
@with_task_logging
def process_lipsync_for_dialogue(self, dialogue_id: str):
    """Launch a Kling lip-sync generation task for a single dialogue segment.

    Steps:
    1. Fetch the `PodcastDialogue` and its parent `PodcastGenerationJob`.
    2. Ensure both an `audio_url` (generated earlier in the pipeline) and a speaker
       reference video are present.
    3. Create a `KlingLipsyncJob` DB row pointing to the audio & reference video.
    4. Fire the `generate_kling_lipsync` Celery task.
    """
    try:
        dialogue = PodcastDialogue.objects.select_related("podcast_job").get(id=dialogue_id)
        job = dialogue.podcast_job

        # Pick the correct speaker video URL
        if dialogue.speaker_name == job.speaker1_name:
            speaker_video = job.speaker1_video_url
        else:
            speaker_video = job.speaker2_video_url

        # Sanity checks -------------------------------------------------------
        if not dialogue.audio_url:
            logger.info(
                "Dialogue %s: audio not ready yet – retrying lipsync launch in 30s",
                dialogue_id,
            )
            raise self.retry(countdown=30)

        if not speaker_video:
            raise RuntimeError(
                f"No speaker video found for dialogue {dialogue_id} (speaker {dialogue.speaker_name})."
            )

        # Create a KlingLipsyncJob row ---------------------------------------
        kling_job = KlingLipsyncJob.objects.create(
            audio_file=dialogue.audio_url,
            video_url=speaker_video,
            client_webhook_url=None,  # handled internally – we poll completion
        )

        # Launch the external task -------------------------------------------
        generate_kling_lipsync.delay(str(kling_job.id))

        # Update dialogue status
        dialogue.status = "lipsync_processing"
        dialogue.save(update_fields=["status"])

    except PodcastDialogue.DoesNotExist:
        logger.error("Dialogue %s not found while launching lipsync", dialogue_id)
    except Exception as exc:
        logger.error("Error in process_lipsync_for_dialogue for %s: %s", dialogue_id, exc)
        raise self.retry(exc=exc)

@app.task(bind=True, max_retries=20, default_retry_delay=60, name="podcast_generator.tasks.check_lipsync_completion")
@with_task_logging
def check_lipsync_completion(self, job_id: str):
    """Poll until every dialogue of the podcast has `lipsync_url` populated."""

    service = PodcastJobService.for_id(job_id)
    job = service.job

    # Any dialogue still processing?
    if job.dialogues.filter(lipsync_url__isnull=True).exists():
        logger.info("Job %s: waiting for lipsync completion – retrying in 60s", job_id)
        raise self.retry()

    logger.info("Job %s: all lipsync videos ready – moving to combination stage", job_id)

    # Mark pipeline progress & kick off combination
    service.transition('final_combination')
    combine_podcast_video.delay(job_id)

# -----------------------------------------------------------------------------
# Helper – start lipsync when *both* audio & speaker videos are ready
# -----------------------------------------------------------------------------

@app.task(bind=True, name="podcast_generator.tasks.try_start_lipsync")
@with_task_logging
def try_start_lipsync(self, job_id):
    """Check if audio and speaker videos are ready; if so, enqueue lipsync."""
    service = PodcastJobService.for_id(job_id)
    job = service.job

    # Preconditions ----------------------------------------------------------
    audio_ready = not job.dialogues.filter(audio_url__isnull=True).exists()
    videos_ready = bool(job.speaker1_video_url)
    if job.speaker_count == 2:
        videos_ready = videos_ready and bool(job.speaker2_video_url)

    if job.skip_lipsync or job.skip_video:
        logger.info("Job %s: lipsync stage skipped due to flags – marking completed.", job_id)
        service.transition('completed')
        return

    if not audio_ready or not videos_ready:
        logger.info("Job %s: lipsync not ready yet (audio_ready=%s, videos_ready=%s).", job_id, audio_ready, videos_ready)
        return  # Will be invoked again by whichever side finishes next

    # Kick off lipsync stage --------------------------------------------------
    if job.status not in {"lipsync_pending", "lipsync_processing", "final_combination", "completed"}:
        service.transition('lipsync_pending')

    enqueue_lipsync_for_dialogues.delay(job_id)

# -----------------------------------------------------------------------------
# FINAL VIDEO COMBINATION
# -----------------------------------------------------------------------------

@app.task(bind=True, max_retries=3, name="podcast_generator.tasks.combine_podcast_video")
@with_task_logging
def combine_podcast_video(self, job_id):
    """Download all lipsynced dialogue videos, concatenate them with FFmpeg, upload
    the resulting podcast video, and mark the job as *completed*.

    This runs entirely on the worker node to avoid yet another external API call.
    """
    service = PodcastJobService.for_id(job_id)
    job = service.job
    dialogues = job.dialogues.order_by('sequence_number')
    if not all(d.lipsync_url for d in dialogues):
        logger.error(f"Job {job_id}: Cannot combine video, some dialogues are missing lipsync_url.")
        raise self.retry(countdown=60)

    service.transition('final_combination')

    try:
        # Create a temporary directory for downloaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            input_files = []
            for i, dialogue in enumerate(dialogues):
                local_path = os.path.join(temp_dir, f"segment_{i}.mp4")
                storage_client.download_file(dialogue.lipsync_url, local_path)
                input_files.append(local_path)

            # Create file list for FFmpeg
            file_list_path = os.path.join(temp_dir, "filelist.txt")
            with open(file_list_path, 'w') as f:
                for file_path in input_files:
                    f.write(f"file '{file_path}'\n")

            # Output path for the final video
            final_video_name = f"podcast_{job_id}.mp4"
            final_video_path = os.path.join(temp_dir, final_video_name)

            # Run FFmpeg to concatenate videos
            ffmpeg_command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', file_list_path,
                '-c', 'copy',
                final_video_path
            ]
            subprocess.run(ffmpeg_command, check=True, capture_output=True)

            # Upload the final video to storage
            with open(final_video_path, 'rb') as f:
                upload_data = storage_client.upload_file(
                    f, endpoint_type='video_generation', filename=final_video_name, include_presigned=True
                )

            if isinstance(upload_data, dict):
                final_video_url = upload_data.get("public_url") or upload_data.get("url")
                final_video_presigned = upload_data.get("presigned_url")
            else:
                final_video_url = upload_data
                final_video_presigned = None

            # Update the job with the final video URLs and mark as completed
            job.final_video_url = final_video_url
            job.final_video_presigned_url = final_video_presigned
            service.transition('completed')
            logger.info(f"Successfully combined and uploaded final video for job {job_id} at {final_video_url}")

    except Exception as e:
        logger.error(f"Failed to combine video for job {job_id}: {e}")
        service.transition('failed', error_message=str(e))
        raise self.retry(exc=e)

# -----------------------------------------------------------------------------
# REAL FUNCTIONS - For our simplified podcast script generator with voice cloning
# ----------------------------------------------------------------------------

@setup_logging.connect
def setup_celery_logging(loglevel=None, **kwargs):
    # 
    #     Setup Celery logging configuration
    #     
    logging.config.dictConfig(settings.LOGGING)

@app.task(bind=True, max_retries=3, name="podcast_generator.tasks.check_final_video_readiness")
@with_task_logging
def check_final_video_readiness(self, job_id):
    """Ensure all prerequisites (lipsync + background) are ready, then launch
    `combine_podcast_video`.
    """
    try:
        job = PodcastGenerationJob.objects.get(id=job_id)

        # Make sure lipsync is completed for every dialogue
        if job.lipsync_status != "completed":
            logger.info(f"Job {job_id}: lipsync not finished yet → waiting.")
            return {"status": "waiting", "reason": "lipsync_incomplete"}

        # Background handling – generate a fake one if the client didn't supply
        if not job.background_image_reference:
            fake_bg_url = f"https://cdn.example.com/images/{job_id}_background.png"
            job.background_image_reference = fake_bg_url
            logger.info(f"Job {job_id}: generated placeholder background {fake_bg_url}")
            job.save(update_fields=["background_image_reference"])

        # Launch final video combination
        combine_podcast_video.delay(str(job_id))
        job.video_combination_status = "processing"
        job.save(update_fields=["video_combination_status"])

        return {"status": "success"}

    except PodcastGenerationJob.DoesNotExist:
        logger.error(f"Job {job_id} does not exist – aborting final video readiness check.")
        return {"status": "error", "message": "Job not found"}
    except Exception as exc:
        logger.error(f"Error in check_final_video_readiness for job {job_id}: {exc}")
        raise self.retry(exc=exc)
