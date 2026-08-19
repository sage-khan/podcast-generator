---
trigger: always_on
---

# Podcast Generator — Project Rules

## Project Identity

- **Name:** podcast-generator
- **Repo:** `git@github.com:sage-khan/podcast-generator.git`
- **Type:** Django-based AI media generation platform (web app + REST API)
- **Purpose:** Generate and fine-tune AI character images, video (incl. lipsync),
  audio/voice, and full AI-scripted podcasts (script → voices → audio/video),
  built on the Replicate API with Celery/Redis for background jobs
- **Author:** Muhammad Danyal (Sage) Khan

## Branching Strategy

- **`main`** — stable, deployable code only. Tag releases when meaningful.
- **`dev`** — active development branch, default for day-to-day work.
- **`feature/*`** — short-lived feature branches cut from `dev`, merged back via PR.

## Open-Source Contributor Guidelines

This project was originally built under a prior client engagement and has since
been genericized for public release. When writing code, docs, or examples here,
think from the perspective of an external contributor who has never seen the
original client context:

- **No internal or client-specific references** — no company names, real domains,
  real IPs/cluster IDs, or proprietary infrastructure details in source, tests,
  docs, or config. All examples must be generic and placeholder-based.
- **Every credential and environment-specific value goes through env/config** —
  no hardcoded API keys, tokens, passwords, domains, or cluster identifiers in
  Python source, YAML manifests, or shell scripts. `.env` (root, gitignored) is
  the single source of real values locally; `.env.example` documents every key
  with a placeholder. Kubernetes secrets follow the same pattern via
  `k8s/01-secrets.yaml` (placeholders, tracked) vs. a local, gitignored copy with
  real values.
- **`misc/` and `media/` are gitignored on purpose** — they hold large/generated
  or scratch content that doesn't belong in the public repo. Don't fight this by
  routing new functional code through either directory.
- **`docs/internal/` is gitignored on purpose** — it holds the original,
  infra-specific versions of docs that have a genericized public counterpart
  (e.g. real Kubernetes/DigitalOcean deployment notes, real CI/CD workflow
  files). Never move something out of `docs/internal/` into a tracked path
  without stripping real credentials/domains/IDs first.
- **Helpful errors** — CLI scripts and API error responses should say what went
  wrong and what to do next, not leak stack traces or internal paths.
- **Docs are part of the code** — update `README.md`, `documentation/`, and
  this rules file when behavior changes. A feature without documentation does
  not exist for external contributors.

## Directory Structure (actual, current)

```
podcast-generator/
├── config/              # Django settings, URLs, Celery app, WSGI/ASGI
├── image_generation/    # Character/pose image generation + LoRA usage
├── video_generation/    # Video generation + lipsync
├── audio_generation/    # TTS + voice cloning
├── model_training/      # LoRA fine-tuning job management
├── podcast_generator/   # Script generation -> voices -> audio/video pipeline
├── playground/          # Internal UI for trying out individual model APIs
├── shared/               # Shared Replicate/storage/webhook clients + utils
├── templates/, static/  # Django-rendered UI (Bootstrap 5)
├── k8s/                 # Kubernetes manifests (DigitalOcean-oriented)
├── deployment/          # Droplet/Docker Compose deployment scripts
├── docs/, documentation/ # API contract, per-model integration notes, prompts
├── docs/internal/        # Gitignored — real infra docs, never made generic
├── scripts/              # Standalone CLI scripts for testing individual APIs
└── tests/                # pytest suite (per-app: serializers/models/tasks/views)
```

Each generation app (`image_generation`, `video_generation`, `audio_generation`,
`model_training`) follows the same Django shape: `models.py`, `serializers.py`,
`tasks.py` (Celery), `views.py`, `urls.py`, `signals.py`. `podcast_generator`
additionally has `services.py` (pipeline orchestration) and `validators.py`.

## Non-Negotiable Rules

1. **No real secrets or infra identifiers ever get committed** — see the
   Open-Source Contributor Guidelines above and `gitops.md`'s Secrets section.
2. **`k8s/*.yaml` manifests stay generic** — real values are supplied at apply
   time via `kubectl create secret --from-env-file` or a local, gitignored copy.
3. **Background/long-running work goes through Celery tasks**, not synchronous
   view logic — Replicate training/inference and video/audio processing are all
   asynchronous by design in this codebase.
4. **External API clients live in `shared/clients/`** — don't inline a new
   Replicate/webhook call in a view when `shared/clients/replicate_client.py` or
   `shared/utils/webhook_utils.py` already has the pattern.

## Testing

- Run `pytest -q` before opening a PR; `tests/conftest.py` and `tests/helpers.py`
  provide fixtures/stubs so tests never hit real external services.
- New features need new tests in the matching app's `tests/<app>/` folder.
- See `tasks.md` at the repo root for the fuller test-suite breakdown.

## Code Style

- Python 3.11+, Django 5.x, DRF for all API endpoints.
- Follow existing per-app file layout (`models.py`/`serializers.py`/`tasks.py`/
  `views.py`/`urls.py`) rather than introducing new organizational patterns.
- Logging via `logging`/Django's logging config in library code; `print` is
  acceptable only in standalone `scripts/`.

## Current Runtime Rules

- Local dev reads from `.env` via `python-dotenv` (see `config/settings.py`).
- Production/CI reads environment variables directly (no `.env` file expected).
- Keep `.claude/rules`, `.cursor/rules`, and `.devin/rules` synchronized —
  they're intentionally identical copies for different AI assistants.
