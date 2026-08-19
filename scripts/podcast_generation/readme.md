# Podcast Generation & Image Editing Orchestration

This folder contains the client–side orchestration script
`scripts/podcast_generation/test_create_podcast_monologue.py`.
It wires together **monologue generation**, **voice-cloning & TTS**,
and the **Flux Kontext image-editing** workflow used to create a
custom podcast cover.

---

## 1  Quick-Start

```bash
# (activate your virtual-env first)

# Image + script + clone + TTS end-to-end
python scripts/podcast_generation/test_create_podcast_monologue.py \
  --project-id  AI-in-Marketing \
  --edit-image  \
  --subject-image-url "https://your-cdn-endpoint.example.com/avatars/austin/images/austin.jpg" \
  --background-image-url "https://your-cdn-endpoint.example.com/background-ref-img/podcast-background-dark.jpg" \
  --image-prompt "Place subject into a podcast studio, preserve subject's face as in the picture." \
  --speaker-name Austin \
  --prompt "In ~30 seconds, talk about AI in digital marketing" \
  --sample-audio-url "https://your-cdn-endpoint.example.com/audio/sample-austin.wav" \
  --generate-voice-clone \
  --generate-TTS \
  --api-base-url https://example.com \
  --username admin --password admin1234
```

### Image-only (cover art) workflow

```bash
python scripts/podcast_generation/test_create_podcast_monologue.py   --project-id AI-in-Marketing   --image-only   --subject-image-url "https://your-cdn-endpoint.example.com/avatars/austin/images/austin.jpg"   --background-image-url "https://your-cdn-endpoint.example.com/background-ref-img/podcast-background-dark.jpg"   --image-prompt "Place subject into a podcast studio, preserve subjects face as in the picture, and keep the podcast studio exactly same"   --image-aspect-ratio "16:9"   --image-output-format png   --image-safety-tolerance 2   --api-base-url https://example.com   --username admin   --password admin1234 --output_dir /path/to/podcast-generator/media/AI-in-Marketing--290625-134322/images \
```

Generated image will be saved as:
```
media/<project>--<timestamp>/images/<project>-<speaker>-<background>.png
```

### Script + audio only (skip image)

Simply omit `--edit-image` / `--edit-image-only`.

---

## 2  CLI Flags (excerpt)

| Flag | Description |
|------|-------------|
| `--project-id` | Base name for the project folder (`<id>--<ddmmyy>-<hhmmss>`). |
| `--project-folder` | Re-use an existing folder instead of creating a new one. |
| `--edit-image` | Generate cover art **and** continue with the rest of the pipeline. |
| `--edit-image-only` (alias `--image-only`) | Run only the image pipeline and exit. |
| `--subject-image-url` | Required URL of the subject image. |
| `--background-image-url` | Optional background; triggers multi-image composition. |
| `--image-prompt` | Text prompt describing the desired edit/composition. |
| `--generate-voice-clone` | Create (or reuse `--voice-id`) a voice clone. |
| `--generate-TTS` | Convert each monologue sentence to audio using the chosen TTS model. |
| `--api-base-url` | Backend base URL for all API calls (defaults to `https://example.com`). |
| `--username` / `--password` | Credentials for authentication (falls back to `API_USERNAME`, `API_PASSWORD`). |

Run with `-h` to see the full list.

---

## 3  Environment Variables

```
# .env or OS env
API_USERNAME=admin
API_PASSWORD=admin1234
API_BASE_URL=https://example.com

DO_SPACES_KEY=xxxxxxxxxxxxxxxxxxxx
DO_SPACES_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=aicc
```

`load_dotenv()` loads `.env`, `.env-do`, and project-root `.env` if present.

---

## 4  Folder & Naming Conventions

```
media/
└─ <project>--<ddmmyy>-<hhmmss>/
   ├─ monologue JSON / TXT files
   ├─ tts/                (audio snippets)
   └─ images/
      └─ <project>-<speaker>-<background>.png
```

No spaces in filenames—camel-cased or dashed.

---

## 5  Change Log (major milestones)

* **v0.1** – initial monologue orchestration.
* **v0.2** – added voice-clone & TTS.
* **v0.3** – integrated Flux Kontext Multi-image & Pro single-image endpoints; `--edit-image` flag.
* **v0.4** – introduced `--edit-image-only`, credential flags, presigned DO Spaces handling, strict naming.

---

Questions or issues? Ping the dev team.