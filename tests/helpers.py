"""Shared dummy helpers and stubs for unit tests.

These helpers avoid importing heavy external dependencies or making
network / filesystem calls. They can be monkey-patched over production
implementations inside tests.
"""
from __future__ import annotations

import io
from typing import List

# ---------------------------------------------------------------------------
# Dummy script generator – replaces the stand-alone script subprocess call
# ---------------------------------------------------------------------------

def dummy_script_generator(prompt: str, speaker_count: int = 1) -> List[str]:
    """Return a static list of dialogue lines for a given prompt."""
    if speaker_count == 1:
        return [f"{prompt} – generated line 1"]
    return [
        f"Speaker 1: {prompt} – line 1",
        "Speaker 2: reply line 1",
    ]


# ---------------------------------------------------------------------------
# Dummy storage client helpers
# ---------------------------------------------------------------------------

def dummy_storage_upload(file_obj: io.BytesIO, filename: str) -> str:  # noqa: D401
    """Pretend to upload a file and return a fake public URL."""
    return f"https://cdn.example.com/{filename}"


def dummy_get_accessible_url(url: str, expires_in: int = 3600) -> str:
    """Return the same URL (bypassing presign logic)."""
    return url


# ---------------------------------------------------------------------------
# Dummy FFmpeg helper – simulate concatenation
# ---------------------------------------------------------------------------

def dummy_ffmpeg_concat(input_files: list[str], output_path: str) -> str:
    """Return *output_path* to simulate successful FFmpeg run."""
    # Normally you'd invoke subprocess; here we just pretend.
    return output_path
