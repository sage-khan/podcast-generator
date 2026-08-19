import pytest
from rest_framework import serializers

from audio_generation.serializers import (
    MinimaxVoiceCloneGenerateSerializer,
    MinimaxSpeechGenerateSerializer,
)


# -----------------------------------------------------------------------------
# MinimaxVoiceCloneGenerateSerializer
# -----------------------------------------------------------------------------

def test_voice_clone_serializer_valid_minimal():
    data = {
        "voice_file": "https://cdn.example.com/voice.wav",
    }
    ser = MinimaxVoiceCloneGenerateSerializer(data=data)
    assert ser.is_valid(), ser.errors


def test_voice_clone_accuracy_bounds():
    data = {
        "voice_file": "https://cdn.example.com/voice.wav",
        "accuracy": 1.2,  # invalid
    }
    ser = MinimaxVoiceCloneGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)


# -----------------------------------------------------------------------------
# MinimaxSpeechGenerateSerializer
# -----------------------------------------------------------------------------

def _base_speech_payload():
    return {"text": "Hello world"}


def test_speech_serializer_valid_defaults():
    ser = MinimaxSpeechGenerateSerializer(data=_base_speech_payload())
    assert ser.is_valid(), ser.errors


def test_speech_text_too_long():
    long_text = "x" * 6000  # exceeds 5000
    ser = MinimaxSpeechGenerateSerializer(data={"text": long_text})
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)


def test_speech_speed_bounds():
    data = _base_speech_payload()
    data["speed"] = 0.3
    ser = MinimaxSpeechGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)


def test_speech_pitch_bounds():
    data = _base_speech_payload()
    data["pitch"] = 20
    ser = MinimaxSpeechGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)


def test_speech_volume_bounds():
    data = _base_speech_payload()
    data["volume"] = 11
    ser = MinimaxSpeechGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)


def test_speech_invalid_sample_rate():
    data = _base_speech_payload()
    data["sample_rate"] = 8000
    ser = MinimaxSpeechGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        ser.is_valid(raise_exception=True)
