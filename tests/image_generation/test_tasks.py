import uuid
from types import SimpleNamespace

import pytest
from django.conf import settings

from image_generation.models import Character
from image_generation.tasks import generate_character as generate_character_task


@pytest.fixture(autouse=True)
def _configure_settings():
    """Ensure essential settings exist for the task."""
    settings.WEBHOOK_BASE_URL = "https://backend.test"  # used to build webhook URL


@pytest.fixture
def character(db):
    return Character.objects.create(
        prompt="A futuristic astronaut fox",
        negative_prompt="",
        image_url="https://cdn.example.com/placeholder.jpg",  # required field
    )


def _stub_replicate(monkeypatch):
    """Patch replicate.predictions.create to avoid external call."""
    dummy_pred = SimpleNamespace(id="pred-123", urls={"get": "https://replicate.example.com/pred-123"})

    class _FakePredictions:
        @staticmethod
        def create(*args, **kwargs):
            return dummy_pred

    import replicate

    monkeypatch.setattr(replicate, "predictions", _FakePredictions())
    return dummy_pred


def _stub_reverse(monkeypatch):
    """Patch django.urls.reverse to avoid URLconf dependency."""
    import image_generation.tasks as task_module

    def _fake_reverse(name, kwargs):
        # Mimic the path we only need to be unique
        return f"/mock-webhook/{kwargs['character_id']}/{kwargs['secret']}/"

    monkeypatch.setattr(task_module, "reverse", _fake_reverse)


def _stub_requests_post(monkeypatch):
    import image_generation.tasks as task_module

    class _Resp(SimpleNamespace):
        status_code = 200

        def raise_for_status(self):
            pass

    monkeypatch.setattr(task_module.requests, "post", lambda *a, **k: _Resp())


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_generate_character_happy_path(monkeypatch, character):
    dummy_pred = _stub_replicate(monkeypatch)
    _stub_reverse(monkeypatch)
    _stub_requests_post(monkeypatch)

    # Run task synchronously via .apply()
    result = generate_character_task.apply(args=(str(character.id),)).get()

    character.refresh_from_db()

    assert character.status == "processing"
    assert character.replicate_prediction_id == dummy_pred.id
    assert result["status"] == "processing"
    assert result["replicate_id"] == dummy_pred.id
