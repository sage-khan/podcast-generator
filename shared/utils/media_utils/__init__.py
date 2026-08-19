"""media_utils
===============
Utility helpers for basic media operations that are frequently needed by
higher-level scripts (e.g. podcast orchestration).  Currently provides:

merge_videos(paths, output_path)
    Concatenate multiple video files (local paths or HTTP/HTTPS URLs) into a
    single MP4 (or other container based on *output_path* extension).

merge_audios(paths, output_path)
    Concatenate multiple audio files (local paths or HTTP/HTTPS URLs) into a
    single audio file (e.g. MP3/WAV) based on *output_path* extension.

A small CLI wrapper is provided so the module can be invoked directly:

    python -m shared.utils.media_utils --videos v1.mp4 v2.mp4 -o merged.mp4
    python -m shared.utils.media_utils --audios a1.mp3 a2.mp3 -o merged.mp3

Notes
-----
1. Requires **ffmpeg** to be available in the system PATH.
2. All input media **must** share the same codec/format parameters for the
   fast *stream-copy* pathway (`-c copy`).  If they don't, set
   `REENCODE=1` in the environment to force a re-encode per file.
3. Remote URLs are downloaded to a temporary directory which is removed after
   processing.
"""

from __future__ import annotations

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests

__all__ = [
    "merge_videos",
    "merge_audios",
]

###############################################################################
# Helper functions
###############################################################################

def _is_url(path: str | os.PathLike) -> bool:
    """Return True if *path* looks like an HTTP(S) URL."""
    if not isinstance(path, str):
        path = str(path)
    return path.startswith("http://") or path.startswith("https://")


def _download(url: str, dest_dir: Path) -> Path:
    """Download *url* to *dest_dir* and return the local Path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    local_path = dest_dir / Path(urlparse(url).path).name
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_path


def _ensure_local(paths: List[str | os.PathLike]) -> tuple[List[Path], list[Path]]:
    """Ensure all *paths* are local.

    Returns (local_paths, temp_dirs)  where *temp_dirs* should be cleaned up by
    the caller when done.
    """
    local_paths: List[Path] = []
    temp_dirs: List[Path] = []

    for p in paths:
        if _is_url(p):
            tmp_dir = Path(tempfile.mkdtemp(prefix="media_merge_"))
            temp_dirs.append(tmp_dir)
            local_paths.append(_download(p, tmp_dir))
        else:
            lp = Path(p).expanduser().resolve()
            if not lp.exists():
                raise FileNotFoundError(str(lp))
            local_paths.append(lp)
    return local_paths, temp_dirs


def _write_concat_file(local_paths: List[Path], concat_list_path: Path) -> None:
    """Write an ffmpeg concat list file given *local_paths*."""
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in local_paths:
            f.write(f"file '{p.as_posix()}'\n")


def _ffmpeg_concat(local_paths: List[Path], output_path: Path, media_type: str) -> None:
    """Run ffmpeg concat to merge *local_paths* into *output_path*.

    *media_type* is either "video" or "audio" (only used for error msgs).
    """
    # Check ffmpeg availability
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg executable not found in PATH")

    reencode = os.getenv("REENCODE", "0") == "1"

    with tempfile.TemporaryDirectory(prefix="concat_list_") as td:
        list_file = Path(td) / "list.txt"
        _write_concat_file(local_paths, list_file)

        cmd = [
            "ffmpeg",
            "-y",  # overwrite
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
        ]

        if reencode:
            if media_type == "video":
                cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"]
            else:
                cmd += ["-c", "mp3"]  # generic; ffmpeg will choose based on ext
        else:
            cmd += ["-c", "copy"]

        cmd.append(str(output_path))

        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)

###############################################################################
# Public API
###############################################################################

def merge_videos(paths: List[str | os.PathLike], output_path: str | os.PathLike) -> Path:
    """Concatenate multiple videos into a single file.

    Parameters
    ----------
    paths: list[str | Path]
        List of file paths or URLs.
    output_path: str | Path
        Destination file (extension determines container, e.g. .mp4).
    """
    output_path = Path(output_path).expanduser().resolve()
    local_paths, tmp_dirs = _ensure_local(paths)
    try:
        _ffmpeg_concat(local_paths, output_path, media_type="video")
    finally:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)
    return output_path


def merge_audios(paths: List[str | os.PathLike], output_path: str | os.PathLike) -> Path:
    """Concatenate multiple audio files into one."""
    output_path = Path(output_path).expanduser().resolve()
    local_paths, tmp_dirs = _ensure_local(paths)
    try:
        _ffmpeg_concat(local_paths, output_path, media_type="audio")
    finally:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)
    return output_path

###############################################################################
# CLI
###############################################################################

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge videos or audios using ffmpeg")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--videos", nargs="+", help="List of video paths/URLs to merge")
    group.add_argument("--audios", nargs="+", help="List of audio paths/URLs to merge")
    parser.add_argument("-o", "--output", required=True, help="Output file path")

    args = parser.parse_args()

    try:
        if args.videos:
            merge_videos(args.videos, args.output)
        else:
            merge_audios(args.audios, args.output)
        print(f"Merged file saved to {args.output}")
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
