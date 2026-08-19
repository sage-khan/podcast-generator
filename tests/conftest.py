import os

# Ensure in-memory / SQLite database is used for tests
os.environ.setdefault("DB_ENGINE", "django.db.backends.sqlite3")
# Dummy placeholders so settings bootstrap doesn't complain
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

# Celery – run tasks eagerly during tests
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
os.environ.setdefault("CELERY_TASK_EAGER_PROPAGATES", "True")

# -----------------------------------------------------------------------------
# Additional reusable fixtures for unit tests
# -----------------------------------------------------------------------------
import uuid
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
import responses

# -----------------------------------------------------------------------------
# Pytest fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def api_client(db):
    """Django Rest Framework API client with JSON defaults."""
    client = APIClient()
    client.defaults["HTTP_ACCEPT"] = "application/json"
    return client


@pytest.fixture
def user(db):
    """Create and return a unique user per test for isolation."""
    User = get_user_model()
    return User.objects.create_user(
        username=f"test_{uuid.uuid4().hex[:8]}",
        email="tester@example.com",
        password="password123",
    )


@pytest.fixture
def job_factory(user):
    """Factory helper for PodcastGenerationJob instances.

    Example:
        job = job_factory(status="pending", speaker_count=2)
    """
    from podcast_generator.models import PodcastGenerationJob

    def _create(**kwargs):
        defaults = dict(
            user=user,
            podcast_idea="Automated test idea",
            speaker_count=1,
            status="pending",
        )
        defaults.update(kwargs)
        return PodcastGenerationJob.objects.create(**defaults)

    return _create


@pytest.fixture
def http_responses():
    """Context-managed `responses` mock for stubbing outbound HTTP calls."""
    with responses.RequestsMock() as rsps:
        yield rsps
