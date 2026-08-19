import pytest
from rest_framework import serializers

from video_generation.serializers import (
    KlingVideoGenerateSerializer,
    KlingLipsyncGenerateSerializer,
    GoogleVeo3GenerateSerializer,
)


# -----------------------------------------------------------------------------
# KlingVideoGenerateSerializer
# -----------------------------------------------------------------------------

def test_kling_video_serializer_valid_minimal():
    """Prompt + start_image (or end_image) should validate."""
    data = {
        "prompt": "A futuristic skyline",
        "start_image": "https://cdn.example.com/frame1.jpg",
    }
    serializer = KlingVideoGenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


def test_kling_video_serializer_requires_start_or_end():
    """Missing both start_image and end_image should raise ValidationError."""
    data = {"prompt": "A city"}
    serializer = KlingVideoGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_kling_video_serializer_invalid_duration():
    """Duration must be 5 or 10 seconds."""
    data = {
        "prompt": "A city",
        "start_image": "https://cdn.example.com/a.jpg",
        "duration": 7,
    }
    serializer = KlingVideoGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


# -----------------------------------------------------------------------------
# KlingLipsyncGenerateSerializer
# -----------------------------------------------------------------------------

def test_kling_lipsync_serializer_voice_speed_bounds():
    data = {
        "text": "Hello world",
        "video_url": "https://cdn.example.com/v.mp4",
        "voice_speed": 2.5,
    }
    serializer = KlingLipsyncGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_kling_lipsync_serializer_mutually_exclusive_video_fields():
    data = {
        "text": "Hello",
        "video_id": "vid-123",
        "video_url": "https://cdn.example.com/v.mp4",
    }
    serializer = KlingLipsyncGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_kling_lipsync_serializer_requires_input_content():
    """Must supply text or audio_file (unless using legacy audio_url)."""
    data = {"video_url": "https://cdn.example.com/v.mp4"}
    serializer = KlingLipsyncGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_kling_lipsync_serializer_valid_legacy():
    data = {
        "audio_url": "https://cdn.example.com/a.mp3",
        "image_url": "https://cdn.example.com/img.jpg",
    }
    serializer = KlingLipsyncGenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


def test_kling_lipsync_serializer_valid_new_schema():
    data = {
        "text": "Greetings",
        "video_url": "https://cdn.example.com/v.mp4",
    }
    serializer = KlingLipsyncGenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


# -----------------------------------------------------------------------------
# GoogleVeo3GenerateSerializer
# -----------------------------------------------------------------------------

def test_google_veo3_serializer_requires_prompt():
    serializer = GoogleVeo3GenerateSerializer(data={})
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_google_veo3_serializer_valid_minimal():
    data = {"prompt": "A dragon flies over mountains"}
    serializer = GoogleVeo3GenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
