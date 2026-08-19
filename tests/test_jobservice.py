#!/usr/bin/env python
"""Unit tests for PodcastJobService state machine.

Run with:
    pytest -q tests/test_jobservice.py
"""

import pytest
from django.contrib.auth import get_user_model
from podcast_generator.models import PodcastGenerationJob
from podcast_generator.services import PodcastJobService

pytestmark = pytest.mark.django_db


@pytest.fixture()
def job():
    """Return a fresh PodcastGenerationJob in `pending` state."""
    User = get_user_model()
    user = User.objects.create_user(username="tester", password="password")
    return PodcastGenerationJob.objects.create(user=user, podcast_idea="Test podcast")


def test_valid_forward_transitions(job):
    svc = PodcastJobService(job)
    expected_flow = PodcastJobService.STATUS_FLOW

    # walk through a subset of valid forward transitions
    path = [
        "script_processing",
        "audio_pending",
        "audio_processing",
        "video_pending",
        "video_processing",
        "completed",
    ]

    for state in path:
        svc.transition(state)
        job.refresh_from_db()
        assert job.status == state


def test_backwards_transition_raises(job):
    svc = PodcastJobService(job)
    svc.transition("script_processing")

    with pytest.raises(ValueError):
        svc.transition("pending")  # backwards is invalid


def test_terminal_state_no_op(job):
    svc = PodcastJobService(job)
    svc.transition("completed")
    job.refresh_from_db()
    assert job.status == "completed"

    # Attempting any further transition should be ignored
    svc.transition("failed")
    job.refresh_from_db()
    assert job.status == "completed"  # unchanged
