"""Unit tests for podcast_generator models, Celery tasks, views & webhooks.

These tests focus on:
- Model defaults and constraint validation for PodcastGenerationJob & PodcastDialogue.
- Celery task `process_podcast_generation` delegating to `PodcastJobService`.
- API endpoints: create job & get status.
- Webhook handlers: voice_clone_webhook & dialogue_audio_webhook.

External side-effects (Celery dispatch, network calls) are stubbed with monkeypatch.
"""

import json
import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework import status

from podcast_generator.models import PodcastGenerationJob, PodcastDialogue
from podcast_generator.tasks import process_podcast_generation as process_task

# -----------------------------------------------------------------------------
# Model tests
# -----------------------------------------------------------------------------


def test_job_default_status(db, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/alice.wav",
        speaker1_image="https://cdn.example.com/alice.png",
    )
    assert job.status == "pending"


def test_job_invalid_status(db, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/alice.wav",
        speaker1_image="https://cdn.example.com/alice.png",
        status="pending",
    )
    job.status = "bogus"
    with pytest.raises(ValidationError):
        job.full_clean()


@pytest.fixture
def dialogue(db, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/alice.wav",
        speaker1_image="https://cdn.example.com/alice.png",
    )
    dlg = PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=1,
        dialogue_text="Hello",
    )
    return dlg


def test_dialogue_default_status(dialogue):
    assert dialogue.status == "pending"


def test_dialogue_invalid_status(dialogue):
    dialogue.status = "oops"
    with pytest.raises(ValidationError):
        dialogue.full_clean()


# -----------------------------------------------------------------------------
# Celery task test – ensure delegation to service
# -----------------------------------------------------------------------------


def test_process_podcast_generation_calls_service(monkeypatch):
    called = {
        "start": False,
        "job_id": None,
    }

    class _DummyService(SimpleNamespace):
        def start_pipeline(self):  # noqa: D401
            called["start"] = True
            return {"status": "started"}

    # Patch PodcastJobService.for_id to return our dummy
    # Patch PodcastJobService.for_id (classmethod) – when accessed via the class
    # Python passes only the *job_id* argument (``cls`` is **not** injected).
    monkeypatch.setattr(
        "podcast_generator.tasks.PodcastJobService.for_id",
        lambda _job_id: _DummyService(),
    )

    dummy_job_id = str(uuid.uuid4())
    result = process_task.apply(args=(dummy_job_id,)).get()

    assert called["start"] is True
    assert result == {"status": "started"}


# -----------------------------------------------------------------------------
# View tests
# -----------------------------------------------------------------------------

@pytest.fixture
def _stub_tasks(monkeypatch):
    # No-op for process_podcast_generation.delay
    monkeypatch.setattr(
        "podcast_generator.tasks.process_podcast_generation.delay", lambda *_a, **_kw: None
    )
    # No-op for downstream readiness checks triggered by webhooks
    monkeypatch.setattr(
        "podcast_generator.tasks.check_video_generation_readiness.delay", lambda *_a, **_kw: None,
        raising=False,
    )
    monkeypatch.setattr(
        "podcast_generator.tasks.process_lipsync.delay", lambda *_a, **_kw: None,
        raising=False,
    )


# ---- create_podcast_generation_job -----------------------------------------


def _valid_create_payload():
    return {
        "podcast_topic": "Test AI podcast",
        "speaker_count": 1,
        "speaker1_name": "Alice",
        "speaker1_audio": "https://cdn.example.com/alice.wav",
        "speaker1_image": "https://cdn.example.com/alice.png",
    }


def test_create_job_view_success(api_client, user, _stub_tasks):
    api_client.force_authenticate(user=user)
    url = reverse("podcast_generator:create_podcast_generation")
    response = api_client.post(url, _valid_create_payload(), format="json")
    assert response.status_code == status.HTTP_201_CREATED
    job_id = response.data["id"]
    job = PodcastGenerationJob.objects.get(id=job_id)
    assert job.podcast_idea == "Test AI podcast"


def test_create_job_view_validation_error(api_client, user, _stub_tasks):
    api_client.force_authenticate(user=user)
    url = reverse("podcast_generator:create_podcast_generation")
    bad_payload = _valid_create_payload()
    bad_payload.pop("speaker1_audio")
    response = api_client.post(url, bad_payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---- get_podcast_generation_status -----------------------------------------


def test_get_status_view(api_client, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/alice.wav",
        speaker1_image="https://cdn.example.com/alice.png",
    )
    api_client.force_authenticate(user=user)
    url = reverse("podcast_generator:get_podcast_generation_status", kwargs={"job_id": job.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(job.id)


# -----------------------------------------------------------------------------
# Webhook tests – voice clone & dialogue audio
# -----------------------------------------------------------------------------


@pytest.fixture
def _stub_webhook_tasks(monkeypatch):
    monkeypatch.setattr(
        "podcast_generator.tasks.check_video_generation_readiness.delay", lambda *_a, **_kw: None,
        raising=False,
    )


# ---- voice_clone_webhook ----------------------------------------------------


def _voice_webhook(job_id, speaker_num, secret):
    path = reverse(
        "podcast_generator:voice_clone_webhook",
        kwargs={"job_id": job_id, "speaker_num": speaker_num},
    )
    return f"{path}?secret={secret}"


def test_voice_clone_webhook_success(api_client, db, user, _stub_webhook_tasks):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
        speaker1_webhook_secret="secret123",
    )

    resp = api_client.post(
        _voice_webhook(job.id, 1, "secret123"),
        json.dumps({"output": "voice_456"}),
        content_type="application/json",
    )
    assert resp.status_code == status.HTTP_200_OK
    job.refresh_from_db()
    assert job.speaker1_voice_id == "voice_456"


def test_voice_clone_webhook_invalid_secret(api_client, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
        speaker1_webhook_secret="secret123",
    )
    resp = api_client.post(_voice_webhook(job.id, 1, "bad"), "{}", content_type="application/json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_voice_clone_webhook_not_found(api_client):
    resp = api_client.post(_voice_webhook(uuid.uuid4(), 1, "x"), "{}", content_type="application/json")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---- dialogue_audio_webhook -------------------------------------------------


def _dialogue_webhook(job_id, dialogue_id, secret):
    path = reverse(
        "podcast_generator:dialogue_audio_webhook",
        kwargs={"job_id": job_id, "dialogue_id": dialogue_id},
    )
    return f"{path}?secret={secret}"


def test_dialogue_audio_webhook_success(api_client, db, user, _stub_webhook_tasks):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
        speaker1_webhook_secret="s1",
    )
    dialogue = PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=1,
        dialogue_text="Hi",
    )

    resp = api_client.post(
        _dialogue_webhook(job.id, dialogue.id, "s1"),
        json.dumps({"output": "https://cdn.example.com/1.mp3"}),
        content_type="application/json",
    )
    assert resp.status_code == status.HTTP_200_OK
    dialogue.refresh_from_db()
    assert dialogue.audio_url == "https://cdn.example.com/1.mp3"


def test_dialogue_audio_webhook_invalid_secret(api_client, user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
        speaker1_webhook_secret="s1",
    )
    dialogue = PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=1,
        dialogue_text="Hi",
    )

    resp = api_client.post(
        _dialogue_webhook(job.id, dialogue.id, "bad"),
        "{}",
        content_type="application/json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_dialogue_audio_webhook_not_found(api_client):
    resp = api_client.post(
        _dialogue_webhook(uuid.uuid4(), uuid.uuid4(), "s1"),
        "{}",
        content_type="application/json",
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
