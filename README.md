# Podcast Generator

A Django-based AI media generation platform: character/image generation with
LoRA fine-tuning, video generation and lipsync, audio/voice synthesis, and a
full text-to-podcast pipeline (script → voices → audio → video). Built on the
[Replicate](https://replicate.com/) API for model inference/training, Celery +
Redis for background jobs, and PostgreSQL for storage.

## What it does

- **Image generation & fine-tuning** — generate character images and pose
  variations, then fine-tune a custom LoRA model per character via Replicate.
- **Video generation** — text/image-to-video and lipsync pipelines (e.g. Kling,
  Google Veo 3).
- **Audio generation** — text-to-speech and voice cloning.
- **Podcast generation** — turns a prompt or source document into a script
  (monologue or multi-speaker dialogue), synthesizes voices, and optionally
  composites a video podcast, with job-status polling throughout.
- **Model training** — manages LoRA fine-tuning jobs and their trained model
  registry.

## Project layout

```
podcast-generator/
├── config/              # Django settings, URLs, Celery app, WSGI/ASGI
├── image_generation/    # Character/pose image generation + LoRA usage
├── video_generation/    # Video generation + lipsync
├── audio_generation/    # TTS + voice cloning
├── model_training/      # LoRA fine-tuning job management
├── podcast_generator/   # Script generation → voices → audio/video pipeline
├── playground/          # Internal UI for trying out individual model APIs
├── shared/              # Shared clients (Replicate), storage, webhooks, utils
├── templates/, static/  # Django-rendered UI (Bootstrap 5)
├── k8s/                 # Kubernetes manifests (DigitalOcean-oriented)
├── deployment/          # Droplet/Docker Compose deployment scripts
├── docs/, documentation/ # API contract, per-model integration notes, prompts
├── scripts/             # Standalone CLI scripts for testing individual APIs
└── tests/               # pytest suite (per-app: serializers/models/tasks/views)
```

Each generation app (`image_generation`, `video_generation`, `audio_generation`,
`model_training`) follows the same Django shape: `models.py`, `serializers.py`,
`tasks.py` (Celery), `views.py`, `urls.py`. `podcast_generator` additionally has
`services.py` (pipeline orchestration) and `validators.py`.

## Setup

1. **Clone and configure environment**
   ```bash
   git clone <this-repo>
   cd podcast-generator
   cp .env.example .env
   ```
   Fill in `.env` with your own credentials — at minimum a Replicate API token,
   a Django secret key, and Postgres connection details. Never commit a real
   `.env`; it's gitignored.

2. **Run with Docker Compose** (recommended — brings up web, Postgres, Redis,
   Celery worker/beat, and Nginx):
   ```bash
   docker compose up --build
   ```

3. **Or run locally** with a virtualenv:
   ```bash
   pip install -r requirements/requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```
   You'll also need Redis running locally for Celery (`celery -A config.celery
   worker --loglevel=info` in a separate shell), and Postgres unless you switch
   `DATABASES` to SQLite for quick local testing.

## API documentation

Interactive API docs are served once the app is running:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Raw OpenAPI schema: `/api/schema/`

See `documentation/api-contract.md` for the full endpoint contract, and
`podcast_generator/README-podcast-generator.md` for the podcast pipeline
specifically. `documentation/` also has per-provider integration notes (Flux,
Kling, Minimax, Google Veo 3, RunwayML, OpenRouter) for the underlying
Replicate/API models this project uses.

## Testing

```bash
pytest -q                          # full suite
pytest tests/video_generation -q   # a single app's tests
pytest --cov=. --cov-report=term-missing
```

Tests are isolated from external services — HTTP calls, storage, and FFmpeg are
stubbed via fixtures in `tests/conftest.py` and `tests/helpers.py`. See
`tasks.md` for a fuller breakdown of the test suite's structure and coverage.

## Deployment

Two supported paths, both documented with real commands:
- **Single droplet + Docker Compose**: `deployment/deploy.sh`,
  `documentation/deployment-digital-ocean.md`.
- **Kubernetes (DigitalOcean)**: `k8s/README.md` for the full walkthrough,
  `k8s/DO-K8s-README.md` for the DOKS-specific shape (cluster, load balancer,
  managed Postgres). CI/CD workflow shapes are documented as
  `docs/github-workflows/*.yml.example` — copy one to `.github/workflows/`,
  fill in the placeholders, and configure the referenced GitHub Secrets.

Every deployment path is configured entirely through environment
variables/`.env` and Kubernetes Secrets — there are no credentials or
environment-specific hostnames committed to this repo. See `k8s/01-secrets.yaml`
and `k8s/02-configmap.yaml` for the full list of variables a deployment needs.

## Contributing

See `.claude/rules/project.md` (also mirrored to `.cursor/rules/` and
`.devin/rules/`) for engineering conventions, directory structure guidance,
and the open-source contribution rules this repo follows — most importantly:
no hardcoded secrets or environment-specific values in source, everything
user-facing goes through `.env`/config.

## License

No license has been chosen yet for this repository — treat it as all-rights-reserved
until a `LICENSE` file is added.
