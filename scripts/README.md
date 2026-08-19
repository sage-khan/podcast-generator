# Podcast Generation Utility Scripts

This directory contains a suite of standalone Python scripts for generating podcasts, from script creation to final video assembly. These scripts are designed to be modular and can be called from the main podcast generation pipeline in `podcast_generator/tasks.py` or used independently for testing and development.

## Common Requirements

All scripts require the following environment variables to be set for API authentication:

- `API_BASE_URL`: The base URL of the Podcast Generator API (e.g., `http://localhost:8000`).
- `API_USERNAME`: Your API username.
- `API_PASSWORD`: Your API password.

These can be set in a `.env` file in the project root or passed as command-line arguments.

## Script Reference

### 1. `generate_monologue_script.py`

Generates a monologue script for a single speaker.

**Usage:**
```bash
python scripts/generate_monologue_script.py --prompt "<your_topic>" --speaker_name "<speaker_name>" --output_dir "<output_directory>"
```

### 2. `generate_dialogue_script.py`

Generates a dialogue script for two speakers.

**Usage:**
```bash
python scripts/generate_dialogue_script.py --prompt "<your_topic>" --speaker_names "<speaker1_name>" "<speaker2_name>" --output_dir "<output_directory>"
```

### 3. `create_voice_clone.py`

Clones a voice from an audio sample.

**Usage:**
```bash
python scripts/create_voice_clone.py --audio_path "<url_or_path_to_audio_sample>" --speaker_name "<speaker_name>" --output_dir "<output_directory>"
```

### 4. `generate_voice.py`

Generates speech from text using a cloned voice.

**Usage:**
```bash
python scripts/generate_voice.py --text "<text_to_speak>" --voice_id "<voice_id>" --speaker_name "<speaker_name>" --output_dir "<output_directory>"
```

### 5. `edit_image.py`

Creates or edits a speaker image. It can generate an image from a text prompt alone, or modify an existing image with a background and a prompt.

**Usage (from prompt):**
```bash
python scripts/edit_image.py --prompt "<image_prompt>" --output_dir "<output_directory>"
```

**Usage (with subject and background):**
```bash
python scripts/edit_image.py --subject_image_url "<url_to_subject_image>" --background_image_url "<url_to_background_image>" --prompt "<editing_prompt>" --output_dir "<output_directory>"
```

### 6. `generate_video.py`

Generates a talking head video from a speaker image.

**Usage:**
```bash
python scripts/generate_video.py --image_url "<url_to_speaker_image>" --output_dir "<output_directory>"
```

### 7. `lipsync_video.py`

Applies lip sync to a video using an audio file.

**Usage:**
```bash
python scripts/lipsync_video.py --video_url "<url_to_video>" --audio_url "<url_to_audio>" --output_dir "<output_directory>"
```
