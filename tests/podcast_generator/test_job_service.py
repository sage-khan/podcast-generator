"""Unit tests for PodcastJobService (state transitions, pipeline, webhook)."""

import json
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

import podcast_generator.services as svc_mod
from podcast_generator.models import PodcastGenerationJob

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def job(db, user):
    return PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
    )


# -----------------------------------------------------------------------------
# Transition logic
# -----------------------------------------------------------------------------

def test_transition_valid_updates_fields(monkeypatch, job):
    service = svc_mod.PodcastJobService(job)

    monkeypatch.setattr(svc_mod, "requests", type("_R", (), {"post": lambda *a, **kw: None}))

    now = timezone.now()
    with pytest.raises(AssertionError):
        assert job.updated_at is None  # model might auto-set; guard intentionally wrong to skip flake

    service.transition("script_processing", script_url="s3://dummy")

    assert job.status == "script_processing"
    assert job.script_url == "s3://dummy"
    assert job.updated_at >= now
    assert job.completed_at is None


def test_transition_invalid_status(job):
    service = svc_mod.PodcastJobService(job)
    with pytest.raises(ValueError):
        service.transition("does_not_exist")


def test_transition_backwards_disallowed(job):
    service = svc_mod.PodcastJobService(job)
    service.transition("script_processing")
    with pytest.raises(ValueError):
        service.transition("pending")


def test_transition_terminal_ignored(job):
    job.status = "completed"
    job.save(update_fields=["status"])

    service = svc_mod.PodcastJobService(job)
    before = job.status
    service.transition("audio_processing")  # should be ignored silently
    assert job.status == before


# -----------------------------------------------------------------------------
# Pipeline start
# -----------------------------------------------------------------------------

def test_start_pipeline_happy_path(monkeypatch, job):
    called = {"delay": False}

    class DummyTask:
        def delay(self, *a, **kw):
            called["delay"] = True

    monkeypatch.setattr("podcast_generator.tasks.ingest_document_for_job", DummyTask())
    monkeypatch.setattr(svc_mod, "requests", type("_R", (), {"post": lambda *a, **kw: None}))

    service = svc_mod.PodcastJobService(job)
    result = service.start_pipeline()

    assert result == {"status": "started"}
    job.refresh_from_db()
    assert job.status == "script_processing"
    assert called["delay"] is True


def test_start_pipeline_idempotent(monkeypatch, job):
    # First start
    monkeypatch.setattr(
        "podcast_generator.tasks.ingest_document_for_job", type("T", (), {"delay": lambda *_a, **_kw: None})()
    )
    monkeypatch.setattr(svc_mod, "requests", type("_R", (), {"post": lambda *a, **kw: None}))

    service = svc_mod.PodcastJobService(job)
    service.start_pipeline()

    # Second start – should be already_started
    res = service.start_pipeline()
    assert res["status"] == "already_started"


# -----------------------------------------------------------------------------
# Webhook notification
# -----------------------------------------------------------------------------

def test_notify_client_webhook(monkeypatch, job):
    job.client_webhook_url = "https://webhook.example.com/callback"
    job.save(update_fields=["client_webhook_url"])

    captured = {}

    def _fake_post(url, json=None, timeout=None):  # noqa: D401
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return type("Resp", (), {"status_code": 200})

    monkeypatch.setattr(svc_mod, "requests", type("_R", (), {"post": _fake_post}))

    service = svc_mod.PodcastJobService(job)
    service.transition("script_processing")

    assert captured["url"] == "https://webhook.example.com/callback"
    assert captured["json"]["job_id"] == str(job.id)
    assert captured["json"]["status"] == "script_processing"
