import uuid
import types
import pytest
from django.contrib.auth import get_user_model
from django.conf import settings
from celery.exceptions import Retry

from podcast_generator.models import PodcastGenerationJob, PodcastDialogue
from podcast_generator.validators import validate_script_json, ValidationError
from podcast_generator.tasks import (
    ingest_document_for_job,
    generate_video_for_speaker,
)

# -----------------------------------------------------------------------------
# Global test config – ensure Celery tasks run synchronously
# -----------------------------------------------------------------------------
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create(username="tester", email="tester@example.com")


# -----------------------------------------------------------------------------
# 1) JSON validation failure
# -----------------------------------------------------------------------------

def test_validate_script_json_invalid_emotion():
    """validate_script_json should raise ValidationError on illegal emotion."""
    bad_json = {
        "speaker": "Alice",
        "text": "Hello world!",
        "emotion": "super-happy"  # not in allowed values
    }
    with pytest.raises(ValidationError):
        validate_script_json([bad_json])


# -----------------------------------------------------------------------------
# 2) PDF ingestion with bad content should not crash pipeline
# -----------------------------------------------------------------------------

def test_pdf_ingestion_bad_bytes(monkeypatch, db, user):
    """ingest_document_for_job should handle an unreadable PDF gracefully."""
    # Create a dummy job that expects a PDF download
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Testing",
        speaker_count=1,
        document_source_url="https://example.com/bogus.pdf",
        status="pending",
    )

    # Mock requests.get to return garbage bytes
    class FakeResp:
        status_code = 200
        content = b"%PDF-1.4 this is not real PDF content"

        def raise_for_status(self):
            pass

    import podcast_generator.tasks as task_module
    monkeypatch.setattr(task_module.requests, "get", lambda *a, **k: FakeResp())

    # Run task synchronously
    ingest_document_for_job.apply(args=(str(job.id),))

    job.refresh_from_db()
    # We expect document_content to be set (possibly empty) but no exception
    assert job.document_content is not None


# -----------------------------------------------------------------------------
# 3) Upload failure during video generation should raise Retry
# -----------------------------------------------------------------------------

def test_upload_failure_retries(monkeypatch, db, user):
    """generate_video_for_speaker should raise Retry when upload fails."""
    # Minimal job with speaker1 image (video generation needs names)
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Topic",
        speaker_count=1,
        speaker1_name="Alice",
        status="video_pending",
    )

    # Mock the upload helper to always raise
    from shared.clients import storage_client as storage_module

    def boom(*args, **kwargs):
        raise RuntimeError("upload failed")

    monkeypatch.setattr(storage_module, "upload_file", boom)

    # Task should raise Retry (captured by Celery) when upload fails.
    with pytest.raises(Retry):
        generate_video_for_speaker.apply(args=(str(job.id), 1))

    # URL fields should still be empty
    job.refresh_from_db()
    assert job.speaker1_video_url is None
    assert job.speaker1_video_presigned_url is None
