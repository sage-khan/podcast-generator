#!/usr/bin/env python3
"""
Orchestrates end-to-end generation of a two-speaker podcast dialogue.

Workflow (see pgen-dialogue.md for full details):
1. Create project folder <project_id>--<ddmmyy>-<hhmmss>
2. Call generate_dialogue_script.py to produce full dialogue text + JSON.
3. Split JSON into two speaker-specific JSONs.
4. In parallel run test_create_podcast_monologue.py twice (one per speaker)
   to generate audio → i2v → lipsync pipelines.
5. When both are done, merge lipsync clips according to the original
   dialogue order and output <project_name>.mp4 in the project root.

This script keeps the same naming/file-structure conventions as the
monologue orchestration.
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import shutil
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import subprocess
from typing import List, Dict

from shared.utils import merge_videos

PROJECT_TS_FMT = "%d%m%y-%H%M%S"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("podcast_dialogue")

################################################################################
# Helper utilities
################################################################################

def run_subprocess_stream(cmd: List[str]) -> int:
    """Run cmd, stream output to logger, return exit code."""
    logger.info("EXEC >> %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout
    for line in proc.stdout:
        logger.info(line.rstrip())
    proc.wait()
    return proc.returncode


def generate_dialogue(prompt: str, speaker_names: List[str], pdf_url: str | None, project_path: Path) -> Path:
    """Call generate_dialogue_script.py and return path to JSON output."""
    output_dir = project_path / "scripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "scripts/podcast_generation/generate_dialogue_script.py",
        "--prompt", prompt,
        "--speaker_names", *speaker_names,
        "--speaker_ids", "1", "2",
        "--output_dir", str(output_dir),
    ]
    if pdf_url:
        cmd += ["--pdf", pdf_url]
    rc = run_subprocess_stream(cmd)
    if rc != 0:
        raise RuntimeError("Dialogue script generation failed")

    # The helper script returns a JSON file name on stdout; fall back to glob.
    json_path = max(output_dir.glob("*_dialogue.json"), key=lambda p: p.stat().st_mtime)
    return json_path


def split_dialogue_json(dialogue_json: Path, project_path: Path, speaker_names: List[str]) -> Dict[str, Path]:
    """Split combined JSON into per-speaker JSONs.

    Returns mapping speaker -> json path.
    """
    data = json.loads(dialogue_json.read_text())
    lines = data.get("lines", [])
    per_spk = {name: [] for name in speaker_names}
    for line in lines:
        name = line["speaker_name"]
        per_spk[name].append(line)

    mapping: Dict[str, Path] = {}
    for name, items in per_spk.items():
        spk_json = project_path / f"{project_path.name}-{name.replace(' ', '-')}-script.json"
        with open(spk_json, "w") as f:
            json.dump(items, f, indent=2)
        mapping[name] = spk_json
    return mapping


def run_monologue_pipeline(project_path: Path, project_id: str, speaker_name: str,
                           sample_audio_url: str, api_base_url: str | None, speaker_json: Path) -> None:
    """Launch monologue pipeline for single speaker (TTS + i2v + lipsync)."""
    # Use a speaker specific sub-folder inside the main project to avoid file clashes
    spk_folder = project_path / speaker_name.replace(" ", "-")
    spk_folder.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "scripts/podcast_generation/test_create_podcast_monologue.py",
        "--project-folder", str(spk_folder),
        "--project-id", f"{project_id}-{speaker_name.replace(' ', '-')}",
        "--prompt", "placeholder",  # not used further
        "--speaker-name", speaker_name,
        "--sample-audio-url", sample_audio_url,
        "--generate-voice-clone",
        "--generate-TTS",
        "--generate-img2vid-silent",
        "--generate-lipsync",
    ]
    if api_base_url:
        cmd += ["--api-base-url", api_base_url]
    rc = run_subprocess_stream(cmd)
    if rc != 0:
        raise RuntimeError(f"Monologue pipeline failed for {speaker_name}")


def collect_lipsync_clips(spk_folder: Path, speaker_name: str) -> List[Path]:
    """Return list of lipsync mp4 paths sorted by index."""
    lipsync_dir = spk_folder / "lipsync"
    clips = sorted(lipsync_dir.glob(f"*{speaker_name.replace(' ', '-')}-lipsync-*.mp4"))
    return clips

################################################################################
# Main
################################################################################

def main():
    p = argparse.ArgumentParser(description="Generate a two-speaker podcast dialogue end-to-end.")
    p.add_argument("--project-id", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--speaker1-name", required=True)
    p.add_argument("--speaker1-audio-url", required=True)
    p.add_argument("--speaker2-name", required=True)
    p.add_argument("--speaker2-audio-url", required=True)
    p.add_argument("--pdf-url", help="Optional context PDF URL")
    p.add_argument("--api-base-url", default=os.environ.get("API_BASE_URL", ""))
    args = p.parse_args()

    # ------------------------------------------------------------------
    # 1. Prepare project folder
    # ------------------------------------------------------------------
    ts = datetime.now().strftime(PROJECT_TS_FMT)
    project_folder_name = f"{args.project_id}--{ts}"
    project_path = Path.cwd() / project_folder_name
    project_path.mkdir(parents=True, exist_ok=True)
    logger.info("Project folder: %s", project_path)

    # ------------------------------------------------------------------
    # 2. Generate dialogue script (text + JSON)
    # ------------------------------------------------------------------
    combined_json = generate_dialogue(
        args.prompt,
        [args.speaker1_name, args.speaker2_name],
        args.pdf_url,
        project_path,
    )
    logger.info("Dialogue JSON: %s", combined_json)

    # ------------------------------------------------------------------
    # 3. Split into per-speaker JSONs
    # ------------------------------------------------------------------
    split_map = split_dialogue_json(
        combined_json,
        project_path,
        [args.speaker1_name, args.speaker2_name],
    )

    # ------------------------------------------------------------------
    # 4. Run monologue pipelines in parallel (TTS, i2v, lipsync)
    # ------------------------------------------------------------------
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_to_name = {
            ex.submit(
                run_monologue_pipeline,
                project_path,
                args.project_id,
                args.speaker1_name,
                args.speaker1_audio_url,
                args.api_base_url,
                split_map[args.speaker1_name],
            ): args.speaker1_name,
            ex.submit(
                run_monologue_pipeline,
                project_path,
                args.project_id,
                args.speaker2_name,
                args.speaker2_audio_url,
                args.api_base_url,
                split_map[args.speaker2_name],
            ): args.speaker2_name,
        }
        for fut in as_completed(fut_to_name):
            name = fut_to_name[fut]
            try:
                fut.result()
            except Exception as e:
                logger.error("Pipeline failed for %s: %s", name, e)
                sys.exit(1)

    # ------------------------------------------------------------------
    # 5. Merge clips according to dialogue order
    # ------------------------------------------------------------------
    order_paths: List[Path] = []
    combined_data = json.loads(combined_json.read_text())
    line_counters = {args.speaker1_name: 1, args.speaker2_name: 1}

    for line in combined_data.get("lines", []):
        spk = line["speaker_name"]
        idx = line_counters[spk]
        line_counters[spk] += 1
        spk_folder = project_path / spk.replace(" ", "-")
        clip_path = spk_folder / "lipsync" / f"{spk_folder.name}-{spk.replace(' ', '-')}-lipsync-{idx}.mp4"
        order_paths.append(clip_path)

    missing = [p for p in order_paths if not p.exists()]
    if missing:
        logger.error("Missing clips: %s", missing)
        sys.exit(1)

    final_video = project_path / f"{project_folder_name}.mp4"
    merge_videos([str(p) for p in order_paths], final_video)
    logger.info("Final dialogue video: %s", final_video)

    return 0


if __name__ == "__main__":
    sys.exit(main())
