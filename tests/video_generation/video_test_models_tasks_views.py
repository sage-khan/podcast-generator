import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from video_generation.models import KlingVideoJob
from video_generation.tasks import generate_kling_video as generate_kling_video_task


# -----------------------------------------------------------------------------
# Model constraint tests
# -----------------------------------------------------------------------------


@pytest.fixture
def kling_job(db):
    return KlingVideoJob.objects.create(
        prompt="A neon city at night",
        start_image="https://cdn.example.com/frame.jpg",
    )


def test_kling_video_default_status(kling_job):
    assert kling_job.status == "starting"


def test_kling_video_invalid_status(kling_job):
    kling_job.status = "not-a-valid-status"
    with pytest.raises(Exception):
        kling_job.full_clean()


# -----------------------------------------------------------------------------
# Celery task tests (generate_kling_video)
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.WEBHOOK_BASE_URL = "https://backend.test"


@pytest.fixture
def _stub_storage(monkeypatch):
    monkeypatch.setattr(
        "video_generation.tasks.storage_client.get_accessible_url", lambda url, expires_in=3600: url
    )


@pytest.fixture
def _stub_send_client_webhook(monkeypatch):
    monkeypatch.setattr("video_generation.tasks.send_client_webhook", lambda *_args, **_kw: None)


@pytest.fixture
def _stub_replicate(monkeypatch):
    """Patch Replicate client used in task to avoid real network."""

    dummy_pred = SimpleNamespace(id="pred-789")

    class _FakePrediction(SimpleNamespace):
        def wait(self):  # pylint: disable=no-self-use
            return "https://cdn.example.com/video.mp4"

    pred_obj = _FakePrediction(id="pred-789")

    class _FakePredictions:
        @staticmethod
        def create(*_args, **_kwargs):
            return pred_obj

    class _FakeClient(SimpleNamespace):
        predictions = _FakePredictions()

    class _FakeReplicateClient:  # pylint: disable=too-few-public-methods
        def __init__(self):
            self.client = _FakeClient()

    monkeypatch.setattr(
        "video_generation.tasks.ReplicateClient", lambda: _FakeReplicateClient()
    )

    return pred_obj


def test_generate_kling_video_happy_path(kling_job, _stub_replicate, _stub_storage, _stub_send_client_webhook):
    # Run task synchronously via .apply()
    result = generate_kling_video_task.apply(args=(str(kling_job.id),)).get()

    kling_job.refresh_from_db()

    assert kling_job.status == "succeeded"
    assert kling_job.output_url == "https://cdn.example.com/video.mp4"
    assert result is None or result.get("status", None) in {None, "succeeded", "processing"}


# -----------------------------------------------------------------------------
# View and webhook tests
# -----------------------------------------------------------------------------


# Helper fixtures for views


@pytest.fixture
def stub_webhook_utils(monkeypatch):
    monkeypatch.setattr("video_generation.views.generate_webhook_secret", lambda: "secret123")
    monkeypatch.setattr(
        "video_generation.views.generate_webhook_url",
        lambda _name, job_id=None, secret=None, request=None, **kw: f"https://webhook.test/{job_id}/{secret}/",
    )


@pytest.fixture
def stub_send_task(monkeypatch):
    # Prevent actual Celery dispatch.
    class _DummyApp(SimpleNamespace):
        def send_task(self, *args, **kwargs):
            return None

    monkeypatch.setattr("video_generation.views.app", _DummyApp())


# generate_kling_video view

def test_generate_kling_video_view_success(api_client, db, stub_webhook_utils, stub_send_task):
    url = reverse("video_generation:generate_kling_video")
    payload = {
        "prompt": "A fantasy forest",
        "start_image": "https://cdn.example.com/first.jpg",
    }
    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["id"]
    job = KlingVideoJob.objects.get(id=job_id)
    assert job.status == "starting"
    assert job.webhook_url.startswith("https://webhook.test/")


def test_generate_kling_video_view_validation_error(api_client, db):
    url = reverse("video_generation:generate_kling_video")
    response = api_client.post(url, {"prompt": "No images"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert KlingVideoJob.objects.count() == 0


# Webhook related fixtures and tests


@pytest.fixture
def kling_job_with_secret(db):
    return KlingVideoJob.objects.create(
        prompt="Placeholder",
        start_image="https://cdn.example.com/frame.jpg",
        webhook_secret="secret123",
    )


@pytest.fixture
def stub_webhook_processing(monkeypatch):
    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: True)
    monkeypatch.setattr("video_generation.views.process_replicate_webhook", lambda *_a, **_kw: True)


@pytest.fixture
def stub_invalid_secret(monkeypatch):
    monkeypatch.setattr("video_generation.views.validate_webhook_secret", lambda *_a, **_kw: False)


def _webhook_url(job_id, secret):
    return reverse(
        "video_generation:kling_video_webhook",
        kwargs={"job_id": job_id, "secret": secret},
    )


def test_kling_video_webhook_success(api_client, kling_job_with_secret, stub_webhook_processing):
    response = api_client.post(_webhook_url(kling_job_with_secret.id, "secret123"), {"status": "completed"}, format="json")
    assert response.status_code == status.HTTP_200_OK


def test_kling_video_webhook_invalid_secret(api_client, kling_job_with_secret, stub_invalid_secret):
    response = api_client.post(_webhook_url(kling_job_with_secret.id, "bad"), {"status": "completed"}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_kling_video_webhook_not_found(api_client):
    fake_id = uuid.uuid4()
    response = api_client.post(_webhook_url(fake_id, "x"), {"status": "completed"}, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
