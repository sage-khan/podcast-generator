"""Unit tests for podcast_generator serializers.

Focus on:
- PodcastGenerationInputSerializer validation and create logic
- PodcastGenerationStatusSerializer progress helper methods

The tests rely on the shared fixtures defined in tests/conftest.py (api_client, user, etc.).
"""

import io
import uuid
from types import SimpleNamespace

import pytest

from podcast_generator.serializers import (
    PodcastGenerationInputSerializer,
    PodcastGenerationStatusSerializer,
)
from podcast_generator.models import PodcastGenerationJob, PodcastDialogue

# -----------------------------------------------------------------------------
# Helpers / shared sample payloads
# -----------------------------------------------------------------------------

def _valid_monologue_payload(**overrides):
    data = {
        "podcast_topic": "The Future of AI Agents",
        "additional_context": "Short intro text.",
        "speaker_count": 1,
        "speaker1_name": "Alice",
        "speaker1_audio": "https://cdn.example.com/alice.wav",
        "speaker1_image": "https://cdn.example.com/alice.png",
    }
    data.update(overrides)
    return data


def _valid_dialogue_payload(**overrides):
    data = {
        "podcast_topic": "The Future of AI Agents – Dialogue",
        "speaker_count": 2,
        "speaker1_name": "Alice",
        "speaker1_audio": "https://cdn.example.com/alice.wav",
        "speaker1_image": "https://cdn.example.com/alice.png",
        "speaker2_name": "Bob",
        "speaker2_audio": "https://cdn.example.com/bob.wav",
        "speaker2_image": "https://cdn.example.com/bob.png",
    }
    data.update(overrides)
    return data


# -----------------------------------------------------------------------------
# Validation tests – monologue
# -----------------------------------------------------------------------------

def test_input_serializer_monologue_valid(user, monkeypatch):
    payload = _valid_monologue_payload()

    # Stub storage_client to avoid real upload when pdf_file is used later
    monkeypatch.setattr(
        "podcast_generator.serializers.storage_client.upload_file",
        lambda *_a, **_kw: "https://cdn.example.com/dummy.pdf",
    )

    serializer = PodcastGenerationInputSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    job = serializer.save(user=user, status="pending")

    assert isinstance(job, PodcastGenerationJob)
    assert job.podcast_idea == payload["podcast_topic"]
    assert job.speaker_count == 1
    assert job.speaker1_name == "Alice"
    assert job.speaker2_name in {None, ""}


@pytest.mark.parametrize(
    "missing_field",
    [
        "speaker1_audio",
        "speaker1_image",
        "speaker1_name",
    ],
)
def test_input_serializer_monologue_required_fields(missing_field):
    payload = _valid_monologue_payload()
    payload.pop(missing_field)
    serializer = PodcastGenerationInputSerializer(data=payload)
    assert not serializer.is_valid()
    assert missing_field in str(serializer.errors)


# -----------------------------------------------------------------------------
# Validation tests – dialogue
# -----------------------------------------------------------------------------

def test_input_serializer_dialogue_valid(user):
    payload = _valid_dialogue_payload()
    serializer = PodcastGenerationInputSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    job = serializer.save(user=user, status="pending")
    assert job.speaker_count == 2
    assert job.speaker2_name == "Bob"


@pytest.mark.parametrize(
    "speaker2_key",
    ["speaker2_audio", "speaker2_image", "speaker2_name"],
)
def test_input_serializer_dialogue_missing_second_speaker(speaker2_key):
    payload = _valid_dialogue_payload()
    payload.pop(speaker2_key)
    serializer = PodcastGenerationInputSerializer(data=payload)
    assert not serializer.is_valid()
    assert speaker2_key in str(serializer.errors)


# -----------------------------------------------------------------------------
# Mutual exclusivity – pdf_url vs pdf_file
# -----------------------------------------------------------------------------

def test_input_serializer_pdf_mutual_exclusive():
    payload = _valid_monologue_payload(
        pdf_url="https://cdn.example.com/doc.pdf",
        pdf_file=io.BytesIO(b"dummy"),
    )
    serializer = PodcastGenerationInputSerializer(data=payload)
    assert not serializer.is_valid()
    # non_field_errors key is expected in serializer errors
    assert "non_field_errors" in serializer.errors


# -----------------------------------------------------------------------------
# Status serializer helpers
# -----------------------------------------------------------------------------

def test_status_serializer_progress_helpers(db):
    job = PodcastGenerationJob.objects.create(
        podcast_idea="Test idea",
        speaker_count=1,
        speaker1_name="Alice",
        speaker1_audio_sample="https://cdn.example.com/a.wav",
        speaker1_image="https://cdn.example.com/a.png",
        status="audio_processing",
    )
    # Add 2 dialogues – one with audio_url to simulate progress
    PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=1,
        dialogue_text="Hello",
        audio_url="https://cdn.example.com/1.mp3",
    )
    PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=2,
        dialogue_text="Hi",
        # no audio_url yet
    )

    serializer = PodcastGenerationStatusSerializer(job)
    data = serializer.data
    assert data["audio_percent"] == 50.0
    assert data["script_completed"] is False
    assert data["audio_completed"] is False
    assert data["video_completed"] is False
