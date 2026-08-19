import pytest
from rest_framework import serializers

from image_generation.serializers import (
    CharacterGenerateSerializer,
    PoseGenerateSerializer,
    FluxKontextProInputSerializer,
)


# -----------------------------------------------------------------------------
# CharacterGenerateSerializer
# -----------------------------------------------------------------------------

def test_character_generate_serializer_valid():
    """Minimal valid payload should pass validation."""
    data = {"prompt": "A cyberpunk cat"}
    serializer = CharacterGenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


# -----------------------------------------------------------------------------
# PoseGenerateSerializer
# -----------------------------------------------------------------------------

def test_pose_generate_serializer_requires_subject_or_character():
    """Serializer should raise error if neither character_id nor subject provided."""
    data = {"prompt": "A smiling pose"}
    serializer = PoseGenerateSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_pose_generate_serializer_valid_with_subject():
    """Providing only subject should be accepted."""
    data = {
        "subject": "https://cdn.example.com/face.jpg",
        "prompt": "3/4 profile shot",
    }
    serializer = PoseGenerateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


# -----------------------------------------------------------------------------
# FluxKontextProInputSerializer
# -----------------------------------------------------------------------------

def test_flux_kontext_pro_input_missing_prompt():
    """Prompt is required; missing prompt should raise ValidationError."""
    data = {
        "input_image": "https://cdn.example.com/photo.png"
    }
    serializer = FluxKontextProInputSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_flux_kontext_pro_input_valid():
    data = {
        "prompt": "Add a neon background",
        "input_image": "https://cdn.example.com/photo.png",
    }
    serializer = FluxKontextProInputSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
