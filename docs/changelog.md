# Changelog

All notable feature and architecture changes to this project are logged here,
newest first. Bug fixes and issue resolutions go in `docs/diagnostics.md`
instead.

## 2026-08-19

### Added: multi-provider LLM adapter layer (`shared/providers/llm/`)

Introduced a framework-agnostic (no Django imports) LLM provider abstraction
so podcast script generation isn't locked to OpenRouter:

- `LLMProvider` interface (`shared/providers/llm/base.py`) — every backend
  exposes the same `chat(messages, model=None, **kwargs) -> str` call.
- `OpenAICompatibleProvider` covers every backend that speaks the OpenAI
  chat-completions REST shape: OpenAI, OpenRouter, Groq, xAI (Grok), and the
  OpenAI-compatible servers exposed by Ollama and vLLM for local inference.
- `AnthropicProvider` and `GeminiProvider` handle the two backends with a
  genuinely different request shape.
- `get_llm_provider()` (`shared/providers/llm/factory.py`) selects a backend
  from the `LLM_PROVIDER` env var (default: `openrouter`, matching prior
  behavior) with an optional `LLM_MODEL` override, and raises a clear error
  naming the missing env var if a required API key isn't set.
- Meta/Llama models aren't a separate provider entry — they're reached by
  setting `LLM_PROVIDER=groq|openrouter|ollama|vllm` with `LLM_MODEL` set to
  a Llama model id, since Meta doesn't operate a hosted inference API of its
  own.
- Rewired the actual call sites — `scripts/generate_monologue_script.py`,
  `scripts/generate_dialogue_script.py`, and their
  `scripts/podcast_generation/` duplicate — off the hardcoded
  `requests.post("https://openrouter.ai/...")` call and onto
  `get_llm_provider()`. Default behavior (OpenRouter + `openai/gpt-4o`) is
  unchanged unless `LLM_PROVIDER`/`LLM_MODEL` are set.

### Added: multi-provider object storage (`shared/clients/storage_client.py`)

Extended `StorageClient` (used by ~30 call sites across the codebase) to
support additional `STORAGE_BACKEND` values without changing its public
interface (`save_url_to_storage`, `upload_file`, `download_file`,
`get_public_url`, `get_accessible_url`):

- `s3` (AWS S3), `gcs` (Google Cloud Storage via its S3-interoperability
  endpoint), and `r2` (Cloudflare R2) now share the same boto3-backed code
  path as the existing `do_spaces` backend — one `S3_LIKE_BACKENDS` set,
  one `_init_s3_like_backend()` method, per-backend env var defaults.
- `azure_blob` added as a distinct code path using the optional
  `azure-storage-blob` SDK (not a hard dependency — selecting this backend
  without the package installed logs a clear error and falls back to local
  storage rather than crashing).
- `do_spaces` behavior and env vars are unchanged — this is additive, not a
  rewrite of the existing DigitalOcean Spaces path.
- New env vars documented in `.env.example` / `environment/.env.example`:
  `AWS_S3_BUCKET`/`AWS_REGION`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`,
  `GCS_BUCKET`/`GCS_HMAC_ACCESS_KEY`/`GCS_HMAC_SECRET`,
  `R2_BUCKET`/`R2_ENDPOINT`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`,
  `AZURE_STORAGE_CONTAINER`/`AZURE_STORAGE_CONNECTION_STRING` (or
  `AZURE_STORAGE_ACCOUNT_URL` + `AZURE_STORAGE_ACCOUNT_KEY`).

### Fixed: stale, incorrect package metadata

`pyproject.toml` and `requirements/requirements.txt` still described an
unrelated "repl-nix-workspace" Flask/SQLAlchemy scaffold (Flask,
Flask-Migrate, Flask-RESTful, Flask-SQLAlchemy, SQLAlchemy, Werkzeug,
Jinja2, click, itsdangerous — none imported anywhere in this codebase,
confirmed by repo-wide grep) left over from an earlier project generator.
Rewrote both to list this project's actual Django/DRF/Celery/Replicate
dependency set. Also removed `pathlib==1.0.1` and `argparse==1.4.0` pins —
both are Python 3 standard-library modules; pinning the identically-named
legacy PyPI backport packages is incorrect on Python 3.11+ and can shadow
the stdlib module.

**Not done as part of this change**: publishing to PyPI. This is a Django
*project* (its own `manage.py`/`settings.py`/`urls.py`), not a reusable
library — see `pyproject.toml`'s trailing comment for the packaging note.
`shared/providers/` is deliberately Django-free so it can be extracted into
its own installable package later if that's worth doing; the Django app
here consumes it as ordinary in-repo code for now.
