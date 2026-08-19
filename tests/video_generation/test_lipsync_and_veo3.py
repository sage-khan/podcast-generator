import os
import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework import status

from video_generation.models import KlingLipsyncJob, GoogleVeo3VideoJob
from video_generation.tasks import (
    generate_kling_lipsync as generate_kling_lipsync_task,
    generate_google_veo3_video as generate_google_veo3_task,
)

# -----------------------------------------------------------------------------
# Common Fixtures & Stubs
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.WEBHOOK_BASE_URL = "https://backend.test"


@pytest.fixture
def stub_send_client_webhook(monkeypatch):
    monkeypatch.setattr("video_generation.tasks.send_client_webhook", lambda *_a, **_kw: None)


@pytest.fixture
def stub_storage(monkeypatch, tmp_path):
    """Stub storage_client to avoid S3/GCS calls."""

    # Create a small dummy audio file that the task can open
    audio_file_path = tmp_path / "audio.mp3"
    audio_file_path.write_bytes(b"0" * 10)  # 10-byte placeholder

    def _download_file(url):  # pylint: disable=unused-argument
        return str(audio_file_path)

    monkeypatch.setattr("video_generation.tasks.storage_client.download_file", _download_file)
    monkeypatch.setattr(
        "video_generation.tasks.storage_client.get_accessible_url", lambda url, expires_in=3600: url
    )

    return str(audio_file_path)


@pytest.fixture
def stub_replicate(monkeypatch):
    """Patch ReplicateClient inside tasks to return deterministic objects."""

    class _FakePrediction(SimpleNamespace):
        def wait(self):  # pylint: disable=no-self-use
            return "https://cdn.example.com/output.mp4"

    prediction_obj = _FakePrediction(id="pred-456")

    class _FakePredictions:
        @staticmethod
        def create(*_args, **_kwargs):
            return prediction_obj

    class _FakeClient(SimpleNamespace):
        predictions = _FakePredictions()

    class _FakeReplicateClient:
        def __init__(self):
            self.client = _FakeClient()

    monkeypatch.setattr("video_generation.tasks.ReplicateClient", lambda: _FakeReplicateClient())

    return prediction_obj


# -----------------------------------------------------------------------------
# Kling Lipsync Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def lipsync_job(db):
    return KlingLipsyncJob.objects.create(
        text="Hello world",
        video_url="https://cdn.example.com/v.mp4",
        audio_file="https://cdn.example.com/a.mp3",
    )


# Model constraints

def test_kling_lipsync_default_status(lipsync_job):
    assert lipsync_job.status == "starting"


def test_kling_lipsync_invalid_status(lipsync_job):
    lipsync_job.status = "oops"
    with pytest.raises(Exception):
        lipsync_job.full_clean()


# Celery task

def test_generate_kling_lipsync_task_happy(lipsync_job, stub_storage, stub_replicate, stub_send_client_webhook):
    generate_kling_lipsync_task.apply(args=(str(lipsync_job.id),)).get()

    lipsync_job.refresh_from_db()
    assert lipsync_job.status == "succeeded"
    assert lipsync_job.output_url == "https://cdn.example.com/output.mp4"


# View + webhook


@pytest.fixture
def stub_webhook_utils(monkeypatch):
    monkeypatch.setattr("video_generation.views.generate_webhook_secret", lambda: "secretLS")
    monkeypatch.setattr(
        "video_generation.views.generate_webhook_url",
        lambda _name, job_id=None, secret=None, request=None, **kw: f"https://webhook.test/{job_id}/{secret}/",
    )


@pytest.fixture
def stub_send_task(monkeypatch):
    # Prevent Celery dispatch from views
    class _Dummy(SimpleNamespace):
        def send_task(self, *args, **kwargs):
            return None

    monkeypatch.setattr("video_generation.views.app", _Dummy())


# generate_kling_lipsync view

def test_generate_kling_lipsync_view_success(api_client, db, stub_webhook_utils, stub_send_task):
    url = reverse("video_generation:generate_kling_lipsync")
    payload = {
        "text": "Testing",
        "video_url": "https://cdn.example.com/v.mp4",
    }
    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["id"]
    assert KlingLipsyncJob.objects.filter(id=job_id).exists()


def test_generate_kling_lipsync_view_validation_error(api_client):
    url = reverse("video_generation:generate_kling_lipsync")
    response = api_client.post(url, {"text": "Only text"}, format="json")  # missing video
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Lipsync webhook


def _ls_webhook(job_id, secret):
    return reverse("video_generation:kling_lipsync_webhook", kwargs={"job_id": job_id, "secret": secret})


@pytest.fixture
def stub_webhook_processing(monkeypatch):
    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: True)
    monkeypatch.setattr("video_generation.views.process_replicate_webhook", lambda *_a, **_kw: True)


def test_kling_lipsync_webhook_success(api_client, lipsync_job, stub_webhook_processing):
    lipsync_job.webhook_secret = "secretLS"
    lipsync_job.save(update_fields=["webhook_secret"])

    res = api_client.post(_ls_webhook(lipsync_job.id, "secretLS"), {"status": "completed"}, format="json")
    assert res.status_code == status.HTTP_200_OK


def test_kling_lipsync_webhook_invalid_secret(api_client, lipsync_job, monkeypatch):
    lipsync_job.webhook_secret = "secretLS"
    lipsync_job.save(update_fields=["webhook_secret"])

    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: False)

    res = api_client.post(_ls_webhook(lipsync_job.id, "bad"), {"status": "completed"}, format="json")
    assert res.status_code == status.HTTP_403_FORBIDDEN


# -----------------------------------------------------------------------------
# Google Veo 3 Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def veo_job(db):
    return GoogleVeo3VideoJob.objects.create(prompt="A dragon over a castle")


# Model constraints

def test_veo_default_status(veo_job):
    assert veo_job.status == "starting"


def test_veo_invalid_status(veo_job):
    veo_job.status = "blah"
    with pytest.raises(Exception):
        veo_job.full_clean()


# Celery task

def test_generate_veo3_task_happy(veo_job, stub_replicate, stub_send_client_webhook):
    generate_google_veo3_task.apply(args=(str(veo_job.id),)).get()

    veo_job.refresh_from_db()
    assert veo_job.status == "succeeded"
    assert veo_job.output_url == "https://cdn.example.com/output.mp4"


# Views and webhook


def test_generate_veo_view_success(api_client, db, stub_webhook_utils, stub_send_task):
    url = reverse("video_generation:generate_google_veo3_video")
    response = api_client.post(url, {"prompt": "A sunset over sea"}, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert GoogleVeo3VideoJob.objects.filter(id=response.data["id"]).exists()


def test_generate_veo_view_validation_error(api_client):
    url = reverse("video_generation:generate_google_veo3_video")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Veo webhook fixtures/helpers


def _veo_webhook(job_id, secret):
    return reverse("video_generation:google_veo3_webhook", kwargs={"job_id": job_id, "secret": secret})


def test_veo_webhook_success(api_client, veo_job, monkeypatch):
    veo_job.webhook_secret = "secretVEO"
    veo_job.save(update_fields=["webhook_secret"])

    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: True)
    monkeypatch.setattr("video_generation.views.process_replicate_webhook", lambda *_a, **_kw: True)

    res = api_client.post(_veo_webhook(veo_job.id, "secretVEO"), {"status": "completed"}, format="json")
    assert res.status_code == status.HTTP_200_OK


def test_veo_webhook_invalid_secret(api_client, veo_job, monkeypatch):
    veo_job.webhook_secret = "secretVEO"
    veo_job.save(update_fields=["webhook_secret"])

    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: False)

    res = api_client.post(_veo_webhook(veo_job.id, "bad"), {"status": "completed"}, format="json")
    assert res.status_code == status.HTTP_403_FORBIDDEN
