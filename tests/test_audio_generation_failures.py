import os
from pathlib import Path

import pytest
from celery.exceptions import Retry
from django.contrib.auth import get_user_model

from podcast_generator.models import PodcastGenerationJob, PodcastDialogue
from podcast_generator.tasks import generate_tts_for_dialogue


@pytest.fixture
def user(db):
    return get_user_model().objects.create(username="audio_user", email="audio@example.com")


@pytest.fixture
def dialogue(user):
    job = PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Audio failure test",
        speaker_count=1,
        speaker1_name="Alice",
        status="audio_pending",
    )
    dlg = PodcastDialogue.objects.create(
        podcast_job=job,
        speaker_name="Alice",
        speaker_voice_id="voice1",
        sequence_number=1,
        dialogue_text="Hello world",
        emotion="neutral",
        status="pending",
    )
    return dlg


def test_audio_generation_retry(monkeypatch, tmp_path, dialogue):
    """generate_tts_for_dialogue should retry when TTS provider fails."""

    # Patch MinimaxSpeechJob.create used inside generate_tts_for_dialogue
    from audio_generation import models as audio_models

    def fail_create(*a, **k):
        raise RuntimeError("TTS provider down")

    monkeypatch.setattr(audio_models.MinimaxSpeechJob, "create", staticmethod(fail_create))

    output_file = tmp_path / "audio.wav"

    with pytest.raises(Retry):
        generate_tts_for_dialogue.apply(args=(str(dialogue.id), "voice1", "Hello", str(output_file)))

    dialogue.refresh_from_db()
    assert dialogue.audio_url is None
