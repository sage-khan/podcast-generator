import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from image_generation.models import Character, Pose


@pytest.fixture
def character(db):
    return Character.objects.create(
        prompt="A medieval knight",
        negative_prompt="",
        image_url="https://cdn.example.com/knight.jpg",
    )


# -----------------------------------------------------------------------------
# Character model constraints
# -----------------------------------------------------------------------------

def test_character_status_choices(character):
    """Assigning an invalid status should fail validation."""
    character.status = "not-a-valid-status"
    with pytest.raises(ValidationError):
        character.full_clean()  # triggers choices validation


def test_character_replicate_prediction_id_unique(character):
    """replicate_prediction_id field is unique across Character instances."""
    character.replicate_prediction_id = "dup-id"
    character.save()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Character.objects.create(
                prompt="Another prompt",
                negative_prompt="",
                image_url="https://cdn.example.com/other.jpg",
                replicate_prediction_id="dup-id",
            )


# -----------------------------------------------------------------------------
# Pose cascade delete
# -----------------------------------------------------------------------------

def test_pose_cascade_delete(character):
    pose = Pose.objects.create(
        character=character,
        image_url="https://cdn.example.com/pose.jpg",
    )

    # Sanity check
    assert Pose.objects.filter(id=pose.id).exists()

    # Delete character should cascade delete pose
    character.delete()
    assert not Pose.objects.filter(id=pose.id).exists()
