from __future__ import annotations

import logging
from typing import List

import requests
from django.conf import settings
from django.utils import timezone

from .models import PodcastGenerationJob

logger = logging.getLogger(__name__)


class PodcastJobService:
    """Central orchestration helper that owns job-level state transitions and
    convenience helpers (webhook notifications, timestamps, etc.).

    Having a single place that mutates ``PodcastGenerationJob`` makes it easier
    to reason about valid status transitions and to avoid duplicating logic
    across Celery tasks and Django views.
    """

    #: Linear allowed flow of *top-level* ``PodcastGenerationJob.status`` values.
    STATUS_FLOW: List[str] = [
        "pending",
        "script_processing",
        "audio_pending",
        "audio_processing",
        "video_pending",
        "video_processing",
        "lipsync_pending",
        "lipsync_processing",
        "final_combination",
        "completed",
        "failed",
    ]

    TERMINAL_STATES = {"completed", "failed"}

    def __init__(self, job: PodcastGenerationJob):
        self.job = job

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @classmethod
    def for_id(cls, job_id: str | int) -> "PodcastJobService":
        """Convenience factory that fetches the job and returns a service
        instance, raising ``PodcastGenerationJob.DoesNotExist`` if missing."""
        job = PodcastGenerationJob.objects.get(id=job_id)
        return cls(job)

    # --------------------------------------------------------------
    # State-machine helpers
    # --------------------------------------------------------------

    def transition(self, new_status: str, **extra_fields):
        """Validate & persist a top-level status transition.

        Args:
            new_status: Target value for ``job.status``.
            **extra_fields: Additional model fields to update atomically.
        """
        if new_status not in self.STATUS_FLOW:
            raise ValueError(f"Invalid status '{new_status}'")

        current_state = self.job.status
        if current_state in self.TERMINAL_STATES:
            logger.warning(
                "Cannot transition terminal job %s (currently %s) to %s",
                self.job.id,
                current_state,
                new_status,
            )
            return  # No exception – silently ignore to keep idempotency

        current_idx = self.STATUS_FLOW.index(current_state)
        new_idx = self.STATUS_FLOW.index(new_status)
        if new_idx < current_idx and new_status not in {"failed"}:
            raise ValueError(
                f"Refusing backwards transition {current_state} → {new_status}"
            )

        # Persist
        setattr(self.job, "status", new_status)
        for k, v in extra_fields.items():
            setattr(self.job, k, v)

        # Timestamps
        self.job.updated_at = timezone.now()
        if new_status in self.TERMINAL_STATES:
            self.job.completed_at = timezone.now()

        update_fields = ["status", "updated_at", *extra_fields.keys()]
        if new_status in self.TERMINAL_STATES:
            update_fields.append("completed_at")

        self.job.save(update_fields=update_fields)
        logger.info("Job %s transitioned %s → %s", self.job.id, current_state, new_status)

        # Notify the outside world
        self._notify_client_webhook()

    # ------------------------------------------------------------------
    # Pipeline entry-point wrappers
    # ------------------------------------------------------------------

    def start_pipeline(self):
        """Kick off the pipeline if it hasn't started yet."""
        if self.job.status not in {"pending", "failed"}:
            logger.info("Job %s already started – status=%s", self.job.id, self.job.status)
            return {"status": "already_started", "current": self.job.status}

        from .tasks import ingest_document_for_job  # local import to avoid cycles

        self.transition("script_processing")
        ingest_document_for_job.delay(str(self.job.id))
        return {"status": "started"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify_client_webhook(self):
        url = self.job.client_webhook_url
        if not url:
            return

        payload = {
            "job_id": str(self.job.id),
            "status": self.job.status,
            "updated_at": self.job.updated_at.isoformat(),
        }
        try:
            timeout = getattr(settings, "PODCAST_WEBHOOK_TIMEOUT", 5)
            requests.post(url, json=payload, timeout=timeout)
            logger.info("Notified client webhook %s for job %s", url, self.job.id)
        except Exception as exc:  # pragma: no cover – best-effort
            logger.warning(
                "Failed to POST webhook %s for job %s: %s", url, self.job.id, exc
            )
