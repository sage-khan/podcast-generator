import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from audio_generation.models import MinimaxVoiceCloneJob, MinimaxSpeechJob
from audio_generation.tasks import (
    generate_minimax_voice_clone as generate_voice_task,
    generate_minimax_speech as generate_speech_task,
)


# -----------------------------------------------------------------------------
# Model constraint tests
# -----------------------------------------------------------------------------

@pytest.fixture
def voice_job(db):
    return MinimaxVoiceCloneJob.objects.create(
        voice_file="https://cdn.example.com/voice.wav",
    )


def test_voice_clone_default_status(voice_job):
    assert voice_job.status == "starting"


def test_voice_clone_invalid_status(voice_job):
    voice_job.status = "bad-status"
    with pytest.raises(Exception):
        voice_job.full_clean()


@pytest.fixture
def speech_job(db):
    return MinimaxSpeechJob.objects.create(
        text="Hello",
        model_version="hd",
    )


def test_speech_default_status(speech_job):
    assert speech_job.status == "starting"


def test_speech_invalid_status(speech_job):
    speech_job.status = "oops"
    with pytest.raises(Exception):
        speech_job.full_clean()


# -----------------------------------------------------------------------------
# Celery task tests
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _settings(settings):
    settings.WEBHOOK_BASE_URL = "https://backend.test"


# ---- Shared stubs -----------------------------------------------------------

@pytest.fixture
def _stub_storage(monkeypatch):
    monkeypatch.setattr(
        "audio_generation.tasks.storage_client.get_accessible_url",
        lambda url, expires_in=3600: url,
    )


@pytest.fixture
def _stub_send_client_webhook(monkeypatch):
    monkeypatch.setattr("audio_generation.tasks.send_client_webhook", lambda *_a, **_kw: None)


# ---- Voice-clone specific ---------------------------------------------------

@pytest.fixture
def _stub_requests(monkeypatch):
    """Patch requests.post used inside voice-clone task to avoid network."""

    class _FakeResp(SimpleNamespace):
        status_code = 201
        text = "CREATED"

        @staticmethod
        def json():
            return {
                "id": "pred-voice-123",
                "urls": {"get": "https://replicate.test/voice/123"},
            }

    monkeypatch.setattr("audio_generation.tasks.requests.post", lambda *_a, **_kw: _FakeResp())


def test_generate_voice_clone_happy_path(
    voice_job, _stub_requests, _stub_storage, _stub_send_client_webhook
):
    result = generate_voice_task.apply(args=(str(voice_job.id),)).get()

    voice_job.refresh_from_db()

    assert voice_job.status == "succeeded"
    assert voice_job.replicate_url == "https://replicate.test/voice/123"
    # output_url may be None if MockPrediction.wait() returns None
    assert result is None or result.get("status", None) in {None, "succeeded", "processing"}


# ---- Speech specific --------------------------------------------------------

@pytest.fixture
def _stub_replicate_speech(monkeypatch):
    """Patch replicate.predictions.create for speech task."""

    class _FakePrediction(SimpleNamespace):
        url = "https://replicate.test/speech/789"
        id = "pred-speech-789"

        @staticmethod
        def wait():  # pylint: disable=no-method-argument
            return "https://cdn.example.com/speech.mp3"

    class _FakePredictions:
        @staticmethod
        def create(*_a, **_kw):  # pylint: disable=unused-argument
            return _FakePrediction()

    class _FakeClient(SimpleNamespace):
        predictions = _FakePredictions()

    monkeypatch.setattr("audio_generation.tasks.replicate", _FakeClient())


def test_generate_speech_happy_path(
    speech_job, _stub_replicate_speech, _stub_storage, _stub_send_client_webhook
):
    result = generate_speech_task.apply(args=(str(speech_job.id),)).get()

    speech_job.refresh_from_db()
    assert speech_job.status == "succeeded"
    assert speech_job.output_url == "https://cdn.example.com/speech.mp3"
    assert result is None or result.get("status", None) in {None, "succeeded", "processing"}


# -----------------------------------------------------------------------------
# View tests & webhook tests
# -----------------------------------------------------------------------------

# Helpers for stubbing inside views

@pytest.fixture
def stub_webhook_utils(monkeypatch):
    monkeypatch.setattr("audio_generation.views.generate_webhook_secret", lambda: "secret123")
    monkeypatch.setattr(
        "audio_generation.views.generate_webhook_url",
        lambda _n, job_id=None, secret=None, request=None, **kw: f"https://webhook.test/{job_id}/{secret}/",
    )


@pytest.fixture
def stub_send_task(monkeypatch):
    class _DummyApp(SimpleNamespace):
        def send_task(self, *_a, **_kw):
            return None

    monkeypatch.setattr("audio_generation.views.app", _DummyApp())


# ---- generate_minimax_voice_clone view --------------------------------------

def test_generate_voice_clone_view_success(api_client, db, stub_webhook_utils, stub_send_task):
    url = reverse("audio_generation:generate_minimax_voice_clone")
    response = api_client.post(
        url,
        {"voice_file": "https://cdn.example.com/voice.wav"},
        format="json",
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["id"]
    job = MinimaxVoiceCloneJob.objects.get(id=job_id)
    assert job.status == "starting"
    assert job.webhook_url.startswith("https://webhook.test/")


def test_generate_voice_clone_view_validation_error(api_client, db):
    url = reverse("audio_generation:generate_minimax_voice_clone")
    response = api_client.post(url, {}, format="json")  # missing voice_file
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert MinimaxVoiceCloneJob.objects.count() == 0


# ---- generate_minimax_speech view ------------------------------------------

def _speech_url(model="hd"):
    if model == "hd":
        return reverse("audio_generation:generate_minimax_speech_hd")
    return reverse("audio_generation:generate_minimax_speech_turbo")


def test_generate_speech_view_success(api_client, db, stub_webhook_utils, stub_send_task):
    response = api_client.post(
        _speech_url("hd"),
        {"text": "Hello there!"},
        format="json",
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["id"]
    job = MinimaxSpeechJob.objects.get(id=job_id)
    assert job.status == "starting"


def test_generate_speech_view_validation_error(api_client, db):
    response = api_client.post(_speech_url("hd"), {}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert MinimaxSpeechJob.objects.count() == 0


# -----------------------------------------------------------------------------
# Webhook fixtures and tests
# -----------------------------------------------------------------------------

@pytest.fixture
def voice_job_with_secret(db):
    return MinimaxVoiceCloneJob.objects.create(
        voice_file="https://cdn.example.com/voice.wav",
        webhook_secret="secret123",
    )


@pytest.fixture
def speech_job_with_secret(db):
    return MinimaxSpeechJob.objects.create(
        text="hi",
        model_version="hd",
        webhook_secret="secret123",
    )


@pytest.fixture
def stub_webhook_processing(monkeypatch):
    monkeypatch.setattr("audio_generation.views.validate_webhook_secret", lambda *_a, **_kw: True)
    monkeypatch.setattr("audio_generation.views.process_replicate_webhook", lambda *_a, **_kw: True)


@pytest.fixture
def stub_invalid_secret(monkeypatch):
    monkeypatch.setattr("audio_generation.views.validate_webhook_secret", lambda *_a, **_kw: False)


# ---- voice clone webhook ----------------------------------------------------

def _voice_webhook(job_id, secret):
    return reverse(
        "audio_generation:minimax_voice_clone_webhook", kwargs={"job_id": job_id, "secret": secret}
    )


def test_voice_clone_webhook_success(api_client, voice_job_with_secret, stub_webhook_processing):
    response = api_client.post(_voice_webhook(voice_job_with_secret.id, "secret123"), {"status": "completed"}, format="json")
    assert response.status_code == status.HTTP_200_OK


def test_voice_clone_webhook_invalid_secret(api_client, voice_job_with_secret, stub_invalid_secret):
    response = api_client.post(_voice_webhook(voice_job_with_secret.id, "bad"), {"status": "x"}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_voice_clone_webhook_not_found(api_client):
    response = api_client.post(_voice_webhook(uuid.uuid4(), "x"), {"status": "x"}, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---- speech webhook ---------------------------------------------------------

def _speech_webhook(job_id, secret):
    return reverse(
        "audio_generation:minimax_speech_webhook", kwargs={"job_id": job_id, "secret": secret}
    )


def test_speech_webhook_success(api_client, speech_job_with_secret, stub_webhook_processing):
    response = api_client.post(_speech_webhook(speech_job_with_secret.id, "secret123"), {"status": "completed"}, format="json")
    assert response.status_code == status.HTTP_200_OK


def test_speech_webhook_invalid_secret(api_client, speech_job_with_secret, stub_invalid_secret):
    response = api_client.post(_speech_webhook(speech_job_with_secret.id, "bad"), {"status": "x"}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_speech_webhook_not_found(api_client):
    response = api_client.post(_speech_webhook(uuid.uuid4(), "x"), {"status": "x"}, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
