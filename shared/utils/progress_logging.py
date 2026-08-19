"""shared.utils.progress_logging
=================================
Utility helpers for emitting *structured* progress updates.

The helper logs JSON-serialisable dictionaries to standard logging so that a
consumer (frontend, monitoring stack, etc.) can parse them easily.

Usage (inside a Celery task)::

    from shared.utils.progress_logging import TaskProgress

    progress = TaskProgress(task_name="generate_tts", stage="audio", total=dialogues.count())
    for i, dialogue in enumerate(dialogues, 1):
        ...  # do work
        progress.update(i)

    # or use convenience wrapper
    progress.complete()

Resulting log line (INFO level):

    {"event": "progress", "task": "generate_tts", "stage": "audio", "current": 5, "total": 10, "percent": 50}

This format is intentionally flat for easy JSON ingestion.
"""

from __future__ import annotations

import logging
import json
from time import time

logger = logging.getLogger(__name__)


class TaskProgress:
    """Encapsulate progress tracking for long-running tasks."""

    __slots__ = ("task_name", "stage", "total", "current", "start_ts")

    def __init__(self, task_name: str, stage: str, total: int):
        self.task_name = task_name
        self.stage = stage
        self.total = max(total, 1)  # avoid div-by-zero
        self.current = 0
        self.start_ts = time()

        # Emit initial 0-progress entry
        self._log()

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    def update(self, current: int | None = None, *, increment: int = 1):
        """Advance progress.

        Provide *current* for an absolute value or *increment*.
        """
        if current is not None:
            self.current = max(0, min(current, self.total))
        else:
            self.current = max(0, min(self.current + increment, self.total))
        self._log()

    def complete(self):
        """Mark progress as finished (100 %)."""
        self.current = self.total
        self._log(final=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, final: bool = False):
        percent = round((self.current / self.total) * 100, 2)
        payload = {
            "event": "progress",
            "task": self.task_name,
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "percent": percent,
            "final": final,
        }
        logger.info(json.dumps(payload))
