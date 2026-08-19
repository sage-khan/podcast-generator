"""Unit tests for podcast_generator utility helpers.

Covers
-------
* validators.validate_script_json (happy path & validation failures)
* tasks.with_task_logging decorator – ensures logging on success & exception.
"""

import logging
from types import SimpleNamespace

import pytest

from podcast_generator.validators import (
    validate_script_json,
    ALLOWED_EMOTIONS,
)
from podcast_generator.tasks import with_task_logging

# -----------------------------------------------------------------------------
# validate_script_json
# -----------------------------------------------------------------------------


def _sample_script(emotion="neutral"):
    return {
        "lines": [
            {"speaker": "Alice", "line": "Hello world", "emotion": emotion},
            {"speaker": "Bob", "line": "Hi", "emotion": emotion},
        ]
    }


def test_validate_script_json_success():
    lines = validate_script_json(_sample_script())
    assert len(lines) == 2
    assert lines[0].text == "Hello world"
    assert lines[0].emotion == "neutral"


@pytest.mark.parametrize("bad_emotion", ["furious", "sadness", "123"])
def test_validate_script_json_invalid_emotion(bad_emotion):
    data = _sample_script(emotion=bad_emotion)
    with pytest.raises(Exception):
        validate_script_json(data)


# -----------------------------------------------------------------------------
# with_task_logging decorator
# -----------------------------------------------------------------------------


def test_with_task_logging_success(caplog):
    caplog.set_level(logging.INFO)

    @with_task_logging
    def dummy(a, b):  # noqa: D401
        return a + b

    result = dummy(2, 3)
    assert result == 5

    msgs = [rec.getMessage() for rec in caplog.records]
    assert any("Starting task" in m for m in msgs)
    assert any("completed successfully" in m for m in msgs)


def test_with_task_logging_exception(caplog):
    caplog.set_level(logging.INFO)

    @with_task_logging
    def dummy_err():  # noqa: D401
        raise ValueError("boom")

    with pytest.raises(ValueError):
        dummy_err()

    msgs = [rec.getMessage() for rec in caplog.records]
    assert any("failed" in m for m in msgs)
