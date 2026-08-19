"""Tests verifying Celery orchestration entry points without executing heavy tasks.

These tests patch the *delay* methods so that we do not actually enqueue tasks –
we merely ensure that the correct downstream task is triggered and that the job
status transitions are persisted.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from podcast_generator.models import PodcastGenerationJob
from podcast_generator.services import PodcastJobService

pytestmark = pytest.mark.django_db


@pytest.fixture()
def job_pending():
    User = get_user_model()
    user = User.objects.create_user("celery", "celery@example.com", "pw")
    return PodcastGenerationJob.objects.create(
        user=user,
        podcast_idea="Celery orchestration demo",
    )


def test_start_pipeline_triggers_script_task(job_pending):
    svc = PodcastJobService(job_pending)

    with patch("podcast_generator.tasks.generate_script_for_job.delay") as mock_delay:
        result = svc.start_pipeline()

    assert result == {"status": "started"}
    mock_delay.assert_called_once_with(str(job_pending.id))

    job_pending.refresh_from_db()
    assert job_pending.status == "script_processing"
