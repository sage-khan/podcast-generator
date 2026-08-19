# AI Media Generation Service – API Contract (v1)

*Last updated: 2025-06-16*

---

## Table of Contents
1. [Base Information](#base-information)
2. [Authentication](#authentication)
3. [Conventions & Error Model](#conventions--error-model)
4. [Endpoint Reference](#endpoint-reference)
   * [Image Generation](#41-image-generation)
   * [Audio Generation](#42-audio-generation)
   * [Video Generation](#43-video-generation)
   * [Model Training](#44-model-training)
   * [Podcast Generator](#45-podcast-generator)
5. [Webhook Call-Backs](#webhook-call-backs)
6. [Rate Limits & SLAs](#rate-limits--slas)
7. [Change Management](#change-management)
8. [OpenAPI Documentation](#openapi-documentation)

---

## Base Information
| Key | Value |
|-----|-------|
| **Base URL (Production)** | `https://example.com/api/` |
| **Base URL (K8S)** | `https://k8s.example.com/api/` |
| **API format** | REST / JSON |
| **Versioning strategy** | URL prefix (`/api/`) – breaking changes bump to `/api/v2/` |
| **Content-Type** | `application/json` |
| **Auth** | Token (see below) |
| **Storage CDN** | `https://your-cdn-endpoint.example.com` |

> All examples use the production domain. Replace with K8S hostnames as required for different environments.

---

## Authentication
### Obtain a token
```http
POST /api/token/ HTTP/1.1
Content-Type: application/json
```
Request body:
```json
{
  "username": "demo", 
  "password": "pass1234"
}
```
Successful response (200):
```json
{ "token": "abc123…" }
```

### Using Token Authentication
Send this token with every subsequent request using the Token prefix:
```
Authorization: Token abc123…
```

### Using Bearer Token Authentication
Alternatively, you can use Bearer token authentication:
```
Authorization: Bearer abc123…
```

Both authentication methods are supported by the API. The Bearer token format is the recommended approach for most API clients and is compatible with standard OAuth 2.0 flows.

---

## Conventions & Error Model
### 1. Asynchronous job envelope
Most “generate” endpoints return **202 Accepted** with a minimal envelope while the job runs in background:
```json
{
  "id": "uuid4",
  "status": "starting",          // starting | processing | succeeded | failed
  "created_at": "2025-06-16T13:02:00Z"
}
```
Poll the companion **status** endpoint (documented per resource) or supply `client_webhook_url` to get push updates.

### 2. Common error responses
| Code | Body |
|------|------|
| 400  | `{ "detail": "validation message" }` |
| 401/403 | `{ "detail": "Authentication credentials were not provided." }` |
| 404  | `{ "detail": "Not found." }` |
| 500  | `{ "error": "internal error message" }` |

---

## Endpoint Reference

### 4.1 Image Generation
Base path: `/api/images/`

#### 4.1.1 Character Image
| Method | Path | Description |
|--------|------|-------------|
| POST | `images/generate/` | Start a new character generation job |
| GET | `images/generate/status/{character_id}/` | Poll job status |

**POST request body**
```jsonc
{
  "prompt": "A cyber-punk fox",
  "negative_prompt": "…",          // optional
  "seed": 42,                      // optional int
  "aspect_ratio": "1:1",          // "1:1", "16:9", etc.
  "image_prompt": "https://…/reference.jpg",    // optional reference img
  "output_format": "jpg",         // jpg | png | webp
  "output_quality": 80,            // 1-100
  "safety_tolerance": 2,           // 0-2 (0 = strict)
  "image_prompt_strength": 0.1,
  "raw": false,
  "client_webhook_url": "https://client.app/wh"  // optional
}
```
**GET response (200)**
```jsonc
{
  "id": "uuid4",
  "prompt": "A cyber-punk fox",
  "status": "succeeded",
  "created_at": "…",
  "image_url": "https://your-cdn-endpoint.example.com/character_generation/output/[filename]",
  "replicate_url": "https://replicate.com/…",
  "output_urls": ["https://your-cdn-endpoint.example.com/character_generation/output/[filename]"],
  "error_message": null
}
```

#### 4.1.2 Pose Generation
Same pattern as above but POST to `images/generate/poses/` with `character_id`, `pose_prompt`, `pose_type`, etc.  See `PoseGenerateSerializer` for the full JSON schema.

#### 4.1.3 LoRA Image (Flux-1)
* POST `images/finetuned/lora/flux-1/`
* GET `images/finetuned/lora/flux-1/{job_id}/`
Request body (excerpt):
```jsonc
{
  "model_id": "model-uuid",
  "prompt": "Cat wearing sunglasses",
  "num_outputs": 4,
  "seed": 1337,
  "go_fast": true,
  "client_webhook_url": "https://…"
}
```
Status fields follow `LoraGenerationStatusSerializer`.

#### 4.1.4 Flux UltraPro / Kontext
| Variant | Start Path | Status Path | Extra fields |
|---------|------------|-------------|--------------|
| UltraPro | `images/generate/flux/1-1/pro/` | `images/generate/flux/1-1/pro/{job_id}/` | *aspect_ratio*, *output_format*, *raw*, … |
| Kontext Pro | `images/generate/flux/kontext/pro/` | `images/generate/flux/kontext/pro/{job_id}/` | |
| Kontext Multi | `images/generate/flux/kontext/multi-image/` | `images/generate/flux/kontext/multi-image/{job_id}/` | `prompt`, `input_image`, etc. |

---

### 4.2 Audio Generation
Base path: `/api/audio/`

#### 4.2.1 Minimax Voice Clone
| Method | Path |
|--------|------|
| POST | `audio/generate/minimax/voice-clone/` |
| GET  | `audio/generate/minimax/voice-clone/{job_id}/` |

POST body:
```jsonc
{
  "voice_file": "https://cdn…/reference.wav",
  "model": "speech-02-turbo",
  "accuracy": 0.7,
  "need_noise_reduction": false,
  "need_volume_normalization": false,
  "client_webhook_url": "https://client.app/wh"
}
```
Success 202 → job envelope.  Status 200 fields = `MinimaxVoiceCloneStatusSerializer` *(includes `voice_id`, `preview`, `output_url`, etc.)*

#### 4.2.2 Minimax Speech (TTS)
Two model variants share the same payload.
| Variant | POST | GET |
|---------|------|-----|
| HD | `audio/generate/minimax/speech-02-hd/` | `audio/generate/minimax/speech-02-hd/{id}/` |
| Turbo | `audio/generate/minimax/speech-02-turbo/` | `audio/generate/minimax/speech-02-turbo/{id}/` |

POST body (full):
```jsonc
{
  "text": "Hello world",
  "voice_id": "Wise_Woman",
  "language": "en",
  "speed": 1.0,
  "pitch": 0,
  "volume": 1.0,
  "bitrate": 128000,
  "channel": "mono",          // mono | stereo
  "emotion": "auto",          // auto, happy, sad, …
  "sample_rate": 32000,
  "language_boost": "None",
  "english_normalization": false,
  "client_webhook_url": "https://…"
}
```
Status → `MinimaxSpeechStatusSerializer` (adds `audio_url`, `replicate_url`, etc.).

---

### 4.3 Video Generation
Base path: `/api/video/`

#### 4.3.1 Kling v1.6 Video
| Method | Path |
|--------|------|
| POST | `video/generate/kling/1-6/pro/` |
| GET  | `video/generate/kling/1-6/pro/{job_id}/` |

POST body (key fields):
```jsonc
{
  "prompt": "Flying car through neon city",
  "negative_prompt": "rain",
  "aspect_ratio": "16:9",
  "start_image": "https://…/frame0.png",
  "end_image": "https://…/frameN.png",
  "reference_images": ["https://…/a.jpg"],
  "cfg_scale": 0.5,
  "duration": 5,
  "client_webhook_url": "https://…"
}
```

#### 4.3.2 Kling Lip-sync
| Method | Path |
|--------|------|
| POST | `video/generate/kling/lipsync/` |
| GET  | `video/generate/kling/lipsync/{job_id}/` |

Two usage modes:
1. **Text → Audio → Video** — supply `text`, optional `voice_id`, `video_url`/`video_id`.
2. **Audio file** — supply `audio_file` and video source.

Request (ex):
```jsonc
{
  "text": "Welcome to the show",
  "voice_id": "en_AOT",
  "voice_speed": 1.2,
  "video_url": "https://cdn…/host.mp4",
  "client_webhook_url": "https://…"
}
```
Status → `KlingLipsyncStatusSerializer` (adds `video_output_url`).

---

### 4.4 Model Training
Base path: `/api/models/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `models/finetune/lora/` | Start LoRA fine-tuning |
| GET  | `models/finetune/lora/{job_id}/` | Job details + status |
| GET  | `models/finetune/lora/status/{job_id}/` | Lightweight status only |

POST body:
```jsonc
{
  "model_name": "my-comic-style",
  "input_image_urls": ["https://…/1.jpg", "https://…/2.jpg"],
  "trigger_word": "comicfox",
  "seed": 123,
  "steps": 1500,
  "lora_rank": 4,
  "resolution": 512,
  "batch_size": 1,
  "learning_rate": 0.0001,
  "client_webhook_url": "https://…"
}
```
Status → `LoraTrainingOutputSerializer`.

---

### 4.5 Podcast Generator
Base path: `/api/podcast/`

| Method | Path | Description |
|--------|------|-------------|
| POST | `podcast/create/` | Kick off full workflow |
| GET  | `podcast/status/{job_id}/` | Aggregate status |
| POST | `podcast/generate-script/` | Generate script only (sync) |

**POST /create body**
```jsonc
{
  "podcast_topic": "AI in 2025",
  "additional_context": "Focus on ethics",
  "speaker_count": 2,
  "speaker1_name": "Alice",
  "speaker1_image": "https://…/alice.png",
  "speaker1_audio": "https://…/alice_sample.wav",
  "speaker2_name": "Bob",
  "speaker2_image": "https://…/bob.png",
  "speaker2_audio": "https://…/bob_sample.wav",
  "client_webhook_url": "https://client.app/pod_wh"
}
```
Status → `PodcastGenerationStatusSerializer` (nested `dialogues` + final video info).

---

## Webhook Call-Backs
The system uses webhooks to notify both internal systems and external clients about job status changes.

### Internal Webhooks
Internal webhooks are automatically configured based on the service environment:

- **Production Environment**: `https://example.com/api/[app_name]/webhooks/[endpoint]`
- **K8S Environment**: `https://k8s.example.com/api/[app_name]/webhooks/[endpoint]`

These webhooks are secured using a webhook secret, which is included in the X-Webhook-Secret header.

### Client Webhooks
Clients may provide a `client_webhook_url` parameter with their job requests to receive push notifications about job status changes. When provided, the system will POST to this URL whenever the job status changes.

Example client webhook payload:
```json
{
  "job_id": "uuid4",
  "status": "succeeded",
  "model": "minimax-voice-clone",
  "updated_at": "2025-06-16T13:12:42Z",
  "result": {
    "voice_id": "voice_clone_123",
    "download_url": "https://your-cdn-endpoint.example.com/audio_generation/output/voice_clones/voice_clone_123.wav"
  }
}
```

### Webhook Retry Policy
- Failed webhook deliveries are retried up to 5 times
- Retries follow an exponential backoff pattern: 1m, 5m, 15m, 30m, 1h
- Webhooks that fail after all retries are logged but not retried further

---

## Rate Limits & SLAs

### Storage Retention Policy
- Generated media files are stored for 30 days from creation
- Media URLs follow this pattern:
  - Character generation: `https://your-cdn-endpoint.example.com/character_generation/output/[filename]`
  - Pose generation: `https://your-cdn-endpoint.example.com/pose_generation/output/[filename]`
  - Model training: `https://your-cdn-endpoint.example.com/model_training/output/[filename]`
  - Model generation: `https://your-cdn-endpoint.example.com/model_generation/output/[filename]`
  - Audio generation: `https://your-cdn-endpoint.example.com/audio_generation/output/[filename]`

### External Service Dependencies
The service relies on the following external APIs:
- Replicate API (AI model inference and training)
  - Owner: `your-replicate-username` (configured via `REPLICATE_OWNER`)
- OpenRouter API (LLM access for script generation)
  - Models: `google/gemini-pro` and `google/gemini-pro-vision`

### Concurrency & Processing Limits
- Concurrent job limits vary by endpoint and are subject to underlying AI service capacity
- Job timeouts:
  - Image generation jobs: 5 minutes
  - Audio generation jobs: 10 minutes
  - Video generation jobs: 15 minutes
  - Model training jobs: 8 hours
  - Podcast generation jobs: 30 minutes

### Target Latency
| Endpoint | Target P95 Latency |
|----------|-------------------|
| Character generation | 30s |
| Pose generation | 45s |
| Audio generation (turbo) | 20s |
| Audio generation (HD) | 60s |
| Video generation | 120s |
| Lipsync generation | 90s |
| LoRA training | 90m |
| Podcast script generation | 60s |
| Full podcast generation | 10m |

---

## Change Management
Breaking changes trigger a **major version bump** (`/api/v2/`) announced ≥ 30 days in advance.  Additive, backwards-compatible changes are documented in release notes and require no immediate action.

---

## OpenAPI Documentation

The service provides OpenAPI/Swagger documentation that can be used for interactive exploration and testing of the API.

### Accessing the Documentation

Swagger UI is available at the following URLs:

- **Production**: `https://example.com/api/docs/`
- **K8S**: `https://k8s.example.com/api/docs/`

Alternative documentation formats:
- **ReDoc UI**: `/api/redoc/` (cleaner, read-only documentation interface)
- **Raw OpenAPI Schema**: `/api/schema/` (JSON format for programmatic access)

### Using Swagger UI

1. Navigate to the Swagger UI URL for your environment
2. Click on the "Authorize" button and enter your API token
3. Expand any endpoint to see the available operations
4. Try out endpoints by filling in the request parameters and clicking "Execute"

### OpenAPI Specification

The raw OpenAPI specification is available at:

- **Production**: `https://example.com/api/schema/`
- **K8S**: `https://k8s.example.com/api/schema/`

You can use this specification to generate client libraries for different programming languages using tools like OpenAPI Generator.

### Client SDKs

No official client SDK is published for this API yet — call the REST endpoints
directly (see examples above) or generate a client from the OpenAPI schema at
`/api/schema/` using a tool like [OpenAPI Generator](https://openapi-generator.tech/).

Example Python usage with `requests`:
```python
import requests

API_BASE = "https://example.com/api"
token = "YOUR_TOKEN"

response = requests.post(
    f"{API_BASE}/images/generate-character/",
    headers={"Authorization": f"Token {token}"},
    json={
        "prompt": "A cyber-punk fox",
        "negative_prompt": "blurry, low quality",
        "guidance_scale": 7.5,
    },
)
print(f"Job ID: {response.json()['id']}")
```

---

*For questions or feature requests, please open an issue on the project's GitHub repository.*
