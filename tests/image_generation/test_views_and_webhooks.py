import json
import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework import status

from image_generation.models import Character


# -----------------------------------------------------------------------------
# Helper fixtures to stub external dependencies used by views
# -----------------------------------------------------------------------------

@pytest.fixture
def stub_webhook_utils(monkeypatch):
    """Patch webhook util helpers used by image_generation.views."""
    # Always return the same secret for repeatability
    monkeypatch.setattr(
        "image_generation.views.generate_webhook_secret", lambda: "secret123"
    )

    # Return a deterministic webhook URL
    def _fake_generate_webhook_url(view_name, character_id=None, secret=None, request=None, **kwargs):  # noqa: D401,E501  # pylint: disable=unused-argument
        return f"https://webhook.test/{character_id}/{secret}/"

    monkeypatch.setattr("image_generation.views.generate_webhook_url", _fake_generate_webhook_url)


@pytest.fixture
def stub_replicate_success(monkeypatch):
    """Patch ReplicateClient so that generate_character succeeds."""

    dummy_pred = SimpleNamespace(id="pred-456")

    class _FakeReplicateClient:  # pylint: disable=too-few-public-methods
        def generate_character(self, *args, **kwargs):  # noqa: D401,E501  # pylint: disable=unused-argument
            return dummy_pred

    monkeypatch.setattr("image_generation.views.ReplicateClient", lambda: _FakeReplicateClient())
    return dummy_pred


@pytest.fixture
def stub_replicate_failure(monkeypatch):
    """Patch ReplicateClient so that generate_character returns None (failure)."""

    class _FakeReplicateClient:  # pylint: disable=too-few-public-methods
        def generate_character(self, *args, **kwargs):  # noqa: D401,E501  # pylint: disable=unused-argument
            return None

    monkeypatch.setattr("image_generation.views.ReplicateClient", lambda: _FakeReplicateClient())


# -----------------------------------------------------------------------------
# generate_character view tests
# -----------------------------------------------------------------------------


def test_generate_character_happy_path(api_client, db, stub_webhook_utils, stub_replicate_success):
    """Valid payload should create job, invoke Replicate and return HTTP 202."""

    url = reverse("image_generation:generate_character")

    payload = {"prompt": "A cyberpunk cat"}
    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED

    # A Character record should have been created with processing status.
    character = Character.objects.get(id=response.data["id"])
    assert character.status == "processing"
    assert character.replicate_prediction_id == stub_replicate_success.id
    assert response.data["replicate_prediction_id"] == stub_replicate_success.id


def test_generate_character_validation_error(api_client, db):
    """Missing required prompt should yield 400 and not create a Character."""

    url = reverse("image_generation:generate_character")
    response = api_client.post(url, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Character.objects.count() == 0


def test_generate_character_replicate_failure(api_client, db, stub_webhook_utils, stub_replicate_failure):
    """If Replicate returns no prediction, view should mark job failed and return 500."""

    url = reverse("image_generation:generate_character")
    payload = {"prompt": "A knight in shining armour"}
    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # The character exists but is marked failed.
    character = Character.objects.first()
    assert character is not None
    assert character.status == "failed"


# -----------------------------------------------------------------------------
# character_webhook view tests
# -----------------------------------------------------------------------------


@pytest.fixture
def character_with_secret(db):
    """Create a Character instance with a known webhook secret."""
    return Character.objects.create(
        prompt="Placeholder prompt",
        image_url="https://cdn.example.com/placeholder.jpg",
        webhook_secret="secret123",
    )


@pytest.fixture
def stub_webhook_processing(monkeypatch):
    """Patch validate_webhook_secret and process_replicate_webhook helpers."""

    def _always_true(*_args, **_kwargs):  # noqa: D401,E501
        return True

    monkeypatch.setattr("image_generation.views.validate_webhook_secret", _always_true)
    monkeypatch.setattr("image_generation.views.process_replicate_webhook", _always_true)


@pytest.fixture
def stub_invalid_secret(monkeypatch):
    """Patch validate_webhook_secret to return False (invalid secret)."""

    monkeypatch.setattr("image_generation.views.validate_webhook_secret", lambda *_: False)


def _webhook_url(char_id, secret):
    return reverse(
        "image_generation:character_webhook",
        kwargs={"character_id": char_id, "secret": secret},
    )


def test_character_webhook_success(api_client, character_with_secret, stub_webhook_processing):
    """Valid webhook call should return HTTP 200."""

    url = _webhook_url(character_with_secret.id, "secret123")
    response = api_client.post(url, {"event": "completed"}, format="json")

    assert response.status_code == status.HTTP_200_OK


def test_character_webhook_invalid_secret(api_client, character_with_secret, stub_invalid_secret):
    """Invalid secret should produce HTTP 403."""

    url = _webhook_url(character_with_secret.id, "wrongsecret")
    response = api_client.post(url, {"event": "completed"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_character_webhook_not_found(api_client):
    """Non-existent character ID should return 404."""

    fake_id = uuid.uuid4()
    url = _webhook_url(fake_id, "whatever")
    response = api_client.post(url, {"event": "completed"}, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
