# Test Suite Overview – `ai_image_gen-and-ft`

This document explains the structure, philosophy, and current coverage of the
`pytest`-based unit-test suite that lives under the `tests/` directory.

---
## 1. Directory layout

```
ai_image_gen-and-ft/
├── tests/
│   ├── conftest.py            # shared fixtures available project-wide
│   │
│   ├── helpers.py             # dummy generators & stubs (script, storage, ffmpeg)
│   │
│   ├── image_generation/
│   │   ├── test_serializers.py
│   │   ├── test_models_tasks_views.py
│   │   └── test_views_webhooks.py
│   │
│   ├── video_generation/
│   │   ├── test_serializers.py
│   │   ├── test_models_tasks_views.py
│   │   └── test_lipsync_and_veo3.py
│   │
│   ├── audio_generation/
│   │   ├── test_serializers.py
│   │   └── test_models_tasks_views.py
│   │
│   ├── podcast_generator/
│   │   ├── test_serializers.py
│   │   ├── test_models_tasks_views.py
│   │   ├── test_job_service.py
│   │   └── test_utilities.py
│   │
│   └── playground/            # placeholder for future tests
└── ...                        # application source code
```

Each app has its own sub-folder mirroring the Django app name.  Tests are split
per concern (serializers, models/tasks/views, misc utilities) to keep files
small and focused.

---
## 2. Shared fixtures (`tests/conftest.py`)

* **`api_client`** – DRF test client with JSON helpers.
* **`user`** – a fresh `django.contrib.auth.get_user_model()` instance.
* **`job_factory`** – convenience helper to build+persist arbitrary *Job* models.
* **HTTP stubs** – monkey-patching of `requests` & storage clients to avoid real
  network traffic.

> When additional external dependencies are introduced, create new reusable
> fixtures here to maximise consistency and minimise boilerplate.

---
## 3. Dummy helpers (`tests/helpers.py`)

Several external services (script generator subprocess, S3 uploads, FFmpeg) are
stubbed by simple Python functions so that unit tests remain deterministic and
fast.  Monkey-patch these helpers onto production modules in tests that would
otherwise hit the network or the filesystem.

---
## 4. Coverage summary (2025-07-01)

| Django app          | Serializers | Models | Celery Tasks | Views / Hooks | Utilities |
|---------------------|------------:|-------:|-------------:|--------------:|-----------:|
| image_generation    | ✅          | ✅     | ✅            | ✅            | n/a        |
| video_generation    | ✅          | ✅     | ✅            | ✅            | n/a        |
| audio_generation    | ✅          | ✅     | ✅            | ✅            | n/a        |
| podcast_generator   | ✅          | ✅     | ✅            | ✅            | ✅         |
| playground          | 🚧          | 🚧     | 🚧            | 🚧            | n/a        |

Overall statement coverage, measured with `pytest --cov`, is **~91 %**.

---
## 5. Running the test suite

```bash
# From repository root
python -m pytest -q                # run everything
python -m pytest tests/video_generation -q   # run a subset

# With coverage report
python -m pytest --cov=./ai_image_gen-and-ft --cov-report=term-missing
```

Tests are isolated from external services; no network or S3 credentials are
required.

---
## 6. Adding new tests

1. Create a new file inside the relevant app folder under `tests/`.
2. Import shared fixtures from `conftest.py`.
3. Stub external side-effects via `monkeypatch` or `helpers.py`.
4. Follow *given / when / then* structure, keeping assertions tight.
5. Run `pytest -q` and ensure **100 %** pass locally **before** opening a PR.

---
## 7. TODO

* Add integration tests for multi-stage pipelines spanning multiple apps.
* Extend `playground/` coverage once that app stabilises.

---
**Maintainers**: Update this document whenever significant test structure or
coverage changes.
