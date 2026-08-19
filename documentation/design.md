# Project Design

Below is a detailed plan outlining our approach to implementing the Character Consistency microservices in Django, based on the updated document details and sample code provided.

---

## 1. High-Level Overview

**Goal:**  
Enable the project team to offer pre-made AI character models that can be fine-tuned and then used to generate images (and potentially video) through the Replicate API.

**Key Features:**

- **Fine-Tune Character Model:**  
  Accept a text description, generate initial images and poses using Flux and the Consistent Character model, fine-tune the model with Flux LoRa training, generate a unique descriptive name, and store the record.

- **List Available Characters:**  
  Retrieve all characters with their unique names and original descriptions.

- **Generate Image with Fine-Tuned Model:**  
  Use a fine-tuned model by passing additional prompts (pose/action and background) to generate an image through Replicate.

*Reference: citeturn1file0*

---

## 2. Technical Architecture in Django

### a. Django Project Setup

- **Framework & Tools:**  
  - Use Django along with Django Rest Framework (DRF) for creating RESTful API endpoints.
  - Use asynchronous task processing (e.g., Celery) for long-running operations such as model training and external API calls.
  - Secure internal endpoints with proper authentication (e.g., API keys or IP whitelisting).

### b. Database Design

- **Character Model:**  
  Create a Django model to store:
  - A **unique character name** (generated using an LLM or custom naming function).
  - The **original text description** provided by the user.
  - (Optionally) additional fields such as a reference to the fine-tuned model version or training status.

*Example:*
```python
from django.db import models

class Character(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
```

### c. External Service Integration via Replicate

We will integrate with multiple models available through Replicate:

1. **AI Image Generation (Flux 1.1):**  
   - **Use case:** Generate the initial AI character image.
   - **Integration:** Use the provided sample code where an image prompt file is passed to Replicate via `replicate.run()`.
   
2. **Consistent Character Generation with Poses:**  
   - **Use case:** Given an image (from Flux or a user upload), generate multiple character poses.
   - **Integration:** Call the Replicate model (e.g., `fofr/consistent-character`) with the generated image as a file/blob and a text prompt.
   
3. **Training Loras (Flux LoRa Trainer):**  
   - **Use case:** Fine-tune a character-specific model using the generated images and training data.
   - **Integration:** Use the training API (`replicate.trainings.create`) with parameters such as steps, lora_rank, and trigger_word. Sample code shows how to initiate training, poll for status, and handle errors.
   
4. **Image Generation from Fine-Tuned Model:**  
   - **Use case:** Once the model is trained, generate images by passing a prompt that combines character details (pose/action) and background description.
   - **Integration:** Use `replicate.run()` with parameters like guidance scale, prompt strength, and number of outputs to get the final generated images.
   
5. **Video Generation (Optional):**  
   - **Use case:** For 1080p video generation using a different Replicate model.
   - **Integration:** Use a similar approach as image generation by passing a start image file and prompt to the model (`kwaivgi/kling-v1.6-pro`).

*Reference: citeturn1file0*

---

## 3. API Endpoints and Process Flow

### a. Fine-Tune Character Model (POST /characters/fine-tune)

**Input:**  
- `description` (string)

**Process Flow:**

1. **Input Validation:**  
   Validate the description using DRF serializers.

2. **Initial Image Generation:**  
   - Call the Flux 1.1 model through Replicate.
   - Pass an image prompt file (or generate one dynamically) along with text prompt parameters.

3. **Pose Generation:**  
   - Use the consistent character model to generate multiple poses from the initial image.
   - Handle file uploads and response parsing.

4. **Fine-Tuning (Lora Training):**  
   - Initiate training using the Flux LoRa trainer model.
   - Provide training inputs (e.g., training images, trigger word, steps) and poll the training status asynchronously if needed.
  
5. **Unique Name Generation:**  
   - Use an LLM or custom logic to generate a descriptive name (e.g., “white_guy_1”).
   - Check the database for uniqueness; if not unique, regenerate.

6. **Database Storage:**  
   - Create a new Character record with the generated name and the original description.

7. **Response:**  
   - Return a JSON response with `name` and `description`.

*Process Diagram:*
```
[Receive Description] 
      ↓
[Generate Initial Image using Flux]
      ↓
[Generate Poses using Consistent Character Model]
      ↓
[Fine-tune Model using Flux LoRa Trainer]
      ↓
[Generate Unique Name]
      ↓
[Store Character in DB]
      ↓
[Return JSON Response]
```

### b. List Available Characters (GET /characters/)

**Input:**  
- No input required.

**Process:**

- Query the Character model from the database.
- Return a list of characters, each with `name` and `description`.

**Response:**
- JSON list of character records.

### c. Generate Image with Fine-Tuned Model (POST /images/generate)

**Input:**  
- `character_name` (string)
- `character_prompt` (string)
- `background_prompt` (string)

**Process Flow:**

1. **Lookup Fine-Tuned Model:**  
   - Use the `character_name` to find the corresponding record.
   - Retrieve any associated model metadata if needed.

2. **Combine Prompts:**  
   - Merge `character_prompt` and `background_prompt` to create a cohesive text prompt.

3. **Generate Image:**  
   - Call the fine-tuned model via Replicate using the combined prompt.
   - Use parameters (e.g., guidance scale, output quality, aspect ratio) as per sample code.

4. **Response:**  
   - Return the generated image URL or image data.

*Process Diagram:*
```
[Receive character_name, character_prompt, background_prompt]
      ↓
[Retrieve Fine-Tuned Model Info from DB]
      ↓
[Merge Prompts]
      ↓
[Call Replicate for Image Generation]
      ↓
[Return Image Data/URL]
```

---

## 4. Implementation Considerations

- **Service Layer:**  
  Separate external API calls into a dedicated service module (e.g., `services/replicate_integration.py`) to keep views thin and maintainable.

- **Asynchronous Processing:**  
  Use Celery (or Django-Q) to handle training and long-running API calls to avoid request timeouts and provide progress tracking.

- **Error Handling & Logging:**  
  Integrate robust logging (e.g., via Sentry) and error-handling mechanisms to capture failures in external API calls.

- **Security:**  
  Secure endpoints for internal use, ensuring that only authorized staff can trigger these endpoints.

- **Testing:**  
  Write unit and integration tests for:
  - API endpoint validation.
  - Service functions that interact with Replicate.
  - Database operations for uniqueness and record integrity.

- **Environment Configuration:**  
  Store API keys and configuration (such as model names and version hashes) in environment variables or Django settings for flexibility.

- **Documentation & Versioning:**  
  Document endpoints using Swagger or DRF’s schema generation tools and plan for API versioning as features evolve.

*Reference: citeturn1file0*

---

## 5. Summary

In summary, our Django-based implementation will feature three main endpoints:

- **/characters/fine-tune:**  
  Processes the character description through a pipeline of image generation (Flux), pose creation (Consistent Character), and model fine-tuning (Flux LoRa Trainer), generating a unique name and storing the record.

- **/characters/:**  
  Lists all stored character models for internal reference.

- **/images/generate:**  
  Generates an image using a fine-tuned model by combining character-specific and background prompts.

This plan leverages Replicate’s API for all heavy lifting in AI image/model generation and keeps our Django code modular, maintainable, and testable. The next step would be to start building out the service modules and corresponding API views.

# Directory Structuring

## Old Style

cc) user@host:~/podcast-generator$ tree
.
├── app-nginx.conf
├── character_gen_lora_ft_flux.py
├── character_gen.py
├── deploy.sh
├── django_character_ai
│   ├── api
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── __init__.py
│   │   ├── migrations
│   │   │   ├── 0001_initial.py
│   │   │   ├── __init__.py
│   │   │   └── __pycache__
│   │   │       ├── 0001_initial.cpython-310.pyc
│   │   │       └── __init__.cpython-310.pyc
│   │   ├── models.py
│   │   ├── __pycache__
│   │   │   ├── admin.cpython-310.pyc
│   │   │   ├── apps.cpython-310.pyc
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── models.cpython-310.pyc
│   │   │   ├── tasks.cpython-310.pyc
│   │   │   ├── views.cpython-310.pyc
│   │   │   └── views_updated.cpython-310.pyc
│   │   ├── tasks.py
│   │   ├── tests.py
│   │   └── views.py
│   ├── celery_app_config.py
│   ├── character_ai
│   │   ├── asgi.py
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── settings.cpython-310.pyc
│   │   │   └── urls.cpython-310.pyc
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── char_generator
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── __init__.py
│   │   ├── migrations
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_character_aspect_ratio_character_image_prompt_and_more.py
│   │   │   ├── 0003_character_replicate_url.py
│   │   │   ├── 0004_loratrainingjob_trainedmodel_additional_params_and_more.py
│   │   │   ├── 0005_rename_additional_params_trainedmodel_training_params_and_more.py
│   │   │   ├── 0006_loratrainingjob_training_started_at.py
│   │   │   ├── 0007_loratrainingjob_webhook_secret_and_more.py
│   │   │   ├── 0008_loragenerationjob.py
│   │   │   ├── 0009_loratrainingjob_logs_and_more.py
│   │   │   ├── 0010_loragenerationjob_webhook_events_filter_used.py
│   │   │   ├── 0011_character_error_message_and_more.py
│   │   │   ├── 0012_character_client_webhook_url_and_more.py
│   │   │   ├── 0013_increase_replicate_model_version_length.py
│   │   │   ├── 0014_loragenerationjob_client_webhook_url_and_more.py
│   │   │   ├── 0015_loragenerationjob_client_webhook_url_and_more.py
│   │   │   ├── __init__.py
│   │   │   └── __pycache__
│   │   │       ├── 0001_initial.cpython-310.pyc
│   │   │       ├── 0002_character_aspect_ratio_character_image_prompt_and_more.cpython-310.pyc
│   │   │       ├── 0003_character_replicate_url.cpython-310.pyc
│   │   │       ├── 0004_loratrainingjob_trainedmodel_additional_params_and_more.cpython-310.pyc
│   │   │       ├── 0005_rename_additional_params_trainedmodel_training_params_and_more.cpython-310.pyc
│   │   │       ├── 0006_loratrainingjob_training_started_at.cpython-310.pyc
│   │   │       ├── 0007_loratrainingjob_webhook_secret_and_more.cpython-310.pyc
│   │   │       ├── 0008_loragenerationjob.cpython-310.pyc
│   │   │       ├── 0009_loratrainingjob_logs_and_more.cpython-310.pyc
│   │   │       ├── 0010_loragenerationjob_webhook_events_filter_used.cpython-310.pyc
│   │   │       ├── 0011_character_error_message_and_more.cpython-310.pyc
│   │   │       ├── 0012_character_client_webhook_url_and_more.cpython-310.pyc
│   │   │       ├── 0013_increase_replicate_model_version_length.cpython-310.pyc
│   │   │       ├── 0014_loragenerationjob_client_webhook_url_and_more.cpython-310.pyc
│   │   │       └── __init__.cpython-310.pyc
│   │   ├── models.py
│   │   ├── __pycache__
│   │   │   ├── admin.cpython-310.pyc
│   │   │   ├── apps.cpython-310.pyc
│   │   │   ├── __init__.cpython-310.pyc
│   │   │   ├── models.cpython-310.pyc
│   │   │   ├── serializers.cpython-310.pyc
│   │   │   └── views.cpython-310.pyc
│   │   ├── serializers.py
│   │   ├── tasks.py
│   │   ├── templates
│   │   │   └── char_generator
│   │   │       └── index.html
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── init.py
│   ├── manage.py
│   ├── staticfiles
│   │   ├── admin
│   │   │   ├── css
│   │   │   │   ├── autocomplete.css
│   │   │   │   ├── base.css
│   │   │   │   ├── changelists.css
│   │   │   │   ├── dark_mode.css
│   │   │   │   ├── dashboard.css
│   │   │   │   ├── forms.css
│   │   │   │   ├── login.css
│   │   │   │   ├── nav_sidebar.css
│   │   │   │   ├── responsive.css
│   │   │   │   ├── responsive_rtl.css
│   │   │   │   ├── rtl.css
│   │   │   │   ├── unusable_password_field.css
│   │   │   │   ├── vendor
│   │   │   │   │   └── select2
│   │   │   │   │       ├── LICENSE-SELECT2.md
│   │   │   │   │       ├── select2.css
│   │   │   │   │       └── select2.min.css
│   │   │   │   └── widgets.css
│   │   │   ├── img
│   │   │   │   ├── calendar-icons.svg
│   │   │   │   ├── gis
│   │   │   │   │   ├── move_vertex_off.svg
│   │   │   │   │   └── move_vertex_on.svg
│   │   │   │   ├── icon-addlink.svg
│   │   │   │   ├── icon-alert.svg
│   │   │   │   ├── icon-calendar.svg
│   │   │   │   ├── icon-changelink.svg
│   │   │   │   ├── icon-clock.svg
│   │   │   │   ├── icon-deletelink.svg
│   │   │   │   ├── icon-hidelink.svg
│   │   │   │   ├── icon-no.svg
│   │   │   │   ├── icon-unknown-alt.svg
│   │   │   │   ├── icon-unknown.svg
│   │   │   │   ├── icon-viewlink.svg
│   │   │   │   ├── icon-yes.svg
│   │   │   │   ├── inline-delete.svg
│   │   │   │   ├── LICENSE
│   │   │   │   ├── README.txt
│   │   │   │   ├── search.svg
│   │   │   │   ├── selector-icons.svg
│   │   │   │   ├── sorting-icons.svg
│   │   │   │   ├── tooltag-add.svg
│   │   │   │   └── tooltag-arrowright.svg
│   │   │   └── js
│   │   │       ├── actions.js
│   │   │       ├── admin
│   │   │       │   ├── DateTimeShortcuts.js
│   │   │       │   └── RelatedObjectLookups.js
│   │   │       ├── autocomplete.js
│   │   │       ├── calendar.js
│   │   │       ├── cancel.js
│   │   │       ├── change_form.js
│   │   │       ├── core.js
│   │   │       ├── filters.js
│   │   │       ├── inlines.js
│   │   │       ├── jquery.init.js
│   │   │       ├── nav_sidebar.js
│   │   │       ├── popup_response.js
│   │   │       ├── prepopulate_init.js
│   │   │       ├── prepopulate.js
│   │   │       ├── SelectBox.js
│   │   │       ├── SelectFilter2.js
│   │   │       ├── theme.js
│   │   │       ├── unusable_password_field.js
│   │   │       ├── urlify.js
│   │   │       └── vendor
│   │   │           ├── jquery
│   │   │           │   ├── jquery.js
│   │   │           │   ├── jquery.min.js
│   │   │           │   └── LICENSE.txt
│   │   │           ├── select2
│   │   │           │   ├── i18n
│   │   │           │   │   ├── af.js
│   │   │           │   │   ├── ar.js
│   │   │           │   │   ├── az.js
│   │   │           │   │   ├── bg.js
│   │   │           │   │   ├── bn.js
│   │   │           │   │   ├── bs.js
│   │   │           │   │   ├── ca.js
│   │   │           │   │   ├── cs.js
│   │   │           │   │   ├── da.js
│   │   │           │   │   ├── de.js
│   │   │           │   │   ├── dsb.js
│   │   │           │   │   ├── el.js
│   │   │           │   │   ├── en.js
│   │   │           │   │   ├── es.js
│   │   │           │   │   ├── et.js
│   │   │           │   │   ├── eu.js
│   │   │           │   │   ├── fa.js
│   │   │           │   │   ├── fi.js
│   │   │           │   │   ├── fr.js
│   │   │           │   │   ├── gl.js
│   │   │           │   │   ├── he.js
│   │   │           │   │   ├── hi.js
│   │   │           │   │   ├── hr.js
│   │   │           │   │   ├── hsb.js
│   │   │           │   │   ├── hu.js
│   │   │           │   │   ├── hy.js
│   │   │           │   │   ├── id.js
│   │   │           │   │   ├── is.js
│   │   │           │   │   ├── it.js
│   │   │           │   │   ├── ja.js
│   │   │           │   │   ├── ka.js
│   │   │           │   │   ├── km.js
│   │   │           │   │   ├── ko.js
│   │   │           │   │   ├── lt.js
│   │   │           │   │   ├── lv.js
│   │   │           │   │   ├── mk.js
│   │   │           │   │   ├── ms.js
│   │   │           │   │   ├── nb.js
│   │   │           │   │   ├── ne.js
│   │   │           │   │   ├── nl.js
│   │   │           │   │   ├── pl.js
│   │   │           │   │   ├── ps.js
│   │   │           │   │   ├── pt-BR.js
│   │   │           │   │   ├── pt.js
│   │   │           │   │   ├── ro.js
│   │   │           │   │   ├── ru.js
│   │   │           │   │   ├── sk.js
│   │   │           │   │   ├── sl.js
│   │   │           │   │   ├── sq.js
│   │   │           │   │   ├── sr-Cyrl.js
│   │   │           │   │   ├── sr.js
│   │   │           │   │   ├── sv.js
│   │   │           │   │   ├── th.js
│   │   │           │   │   ├── tk.js
│   │   │           │   │   ├── tr.js
│   │   │           │   │   ├── uk.js
│   │   │           │   │   ├── vi.js
│   │   │           │   │   ├── zh-CN.js
│   │   │           │   │   └── zh-TW.js
│   │   │           │   ├── LICENSE.md
│   │   │           │   ├── select2.full.js
│   │   │           │   └── select2.full.min.js
│   │   │           └── xregexp
│   │   │               ├── LICENSE.txt
│   │   │               ├── xregexp.js
│   │   │               └── xregexp.min.js
│   │   └── rest_framework
│   │       ├── css
│   │       │   ├── bootstrap.min.css
│   │       │   ├── bootstrap.min.css.map
│   │       │   ├── bootstrap-theme.min.css
│   │       │   ├── bootstrap-theme.min.css.map
│   │       │   ├── bootstrap-tweaks.css
│   │       │   ├── default.css
│   │       │   ├── font-awesome-4.0.3.css
│   │       │   └── prettify.css
│   │       ├── docs
│   │       │   ├── css
│   │       │   │   ├── base.css
│   │       │   │   ├── highlight.css
│   │       │   │   └── jquery.json-view.min.css
│   │       │   ├── img
│   │       │   │   ├── favicon.ico
│   │       │   │   └── grid.png
│   │       │   └── js
│   │       │       ├── api.js
│   │       │       ├── highlight.pack.js
│   │       │       └── jquery.json-view.min.js
│   │       ├── fonts
│   │       │   ├── fontawesome-webfont.eot
│   │       │   ├── fontawesome-webfont.svg
│   │       │   ├── fontawesome-webfont.ttf
│   │       │   ├── fontawesome-webfont.woff
│   │       │   ├── glyphicons-halflings-regular.eot
│   │       │   ├── glyphicons-halflings-regular.svg
│   │       │   ├── glyphicons-halflings-regular.ttf
│   │       │   ├── glyphicons-halflings-regular.woff
│   │       │   └── glyphicons-halflings-regular.woff2
│   │       ├── img
│   │       │   ├── glyphicons-halflings.png
│   │       │   ├── glyphicons-halflings-white.png
│   │       │   └── grid.png
│   │       └── js
│   │           ├── ajax-form.js
│   │           ├── bootstrap.min.js
│   │           ├── coreapi-0.1.1.js
│   │           ├── csrf.js
│   │           ├── default.js
│   │           ├── jquery-3.7.1.min.js
│   │           ├── load-ajax-form.js
│   │           └── prettify-min.js
│   └── utils
│       ├── client_webhook.py
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-310.pyc
│       │   ├── replicate_client.cpython-310.pyc
│       │   └── storage.cpython-310.pyc
│       ├── replicate_client.py
│       └── storage.py
├── Django_image_consistent_api_tester.ipynb
├── docker-compose.yml
├── docker-entrypoint.sh
├── Dockerfile
├── documentation
│   ├── blackforestlabs-flux-1-1-ultrapro-docs.md
│   ├── Character Consistency-django-app-1.docx
│   ├── deployment-digital-ocean.md
│   ├── deploymentguide.docx
│   ├── design.md
│   ├── fofr-character-consistency.md
│   ├── Microservice Deployment Strategy.docx
│   ├── ostris-lora-dev-trainer.md
│   └── README-webhook-replicate-python.md
├── downloads
│   ├── character_db43d882-a539-4ac6-bad2-ee6ddc4d4c78.jpg
│   ├── character_def53253-bdc0-4b23-b4a3-9cb8c89a7195.jpg
│   ├── character_e5ec84d4-b0ca-4601-ac64-458362fe7477.jpg
│   ├── character_f6190294-0853-4eb6-86af-7366bd8c1dbe.jpg
│   └── poses
├── finetuned_model_img_generator_noapi.py
├── finetune_lora_flux.py
├── finetune-test-no-django-api.py
├── generated-icon.png
├── github-workflows
│   ├── deploy-droplet.yml
│   └── deploy-k8s-DO.yml
├── gunicorn.conf.py
├── init-ssl-fix.sh
├── init-ssl.sh
├── k8s
│   ├── 00-namespace.yaml
│   ├── 01-secrets.yaml
│   ├── 02-configmap.yaml
│   ├── 03-postgres-pvc.yaml
│   ├── 04-postgres-deployment.yaml
│   ├── 05-redis-deployment.yaml
│   ├── 06-web-deployment.yaml
│   ├── 07-celery-deployment.yaml
│   ├── 08-celery-beat-deployment.yaml
│   ├── 09-nginx-config.yaml
│   ├── 10-nginx-deployment.yaml
│   ├── 11-services.yaml
│   ├── 12-ingress.yaml
│   ├── 13-cert-issuer.yaml
│   └── my-django-deploy-k8s-cluster-kubeconfig.yaml
├── k8s-manifests.sh
├── media
├── nginx
│   └── app.conf
├── poses_generator.py
├── postgres-deployment-backup.yaml
├── project_requirements.txt
├── pyproject.toml
├── README.md
├── requirements-docker.txt
├── setup_django_old.py
├── setup_django.py
├── static
│   ├── css
│   │   └── custom.css
│   └── js
│       └── app.js
├── templates
│   ├── 404.html
│   ├── 500.html
│   ├── base.html
│   ├── character_generator.html
│   ├── index.html
│   ├── model_gallery.html
│   ├── model_trainer.html
│   └── pose_generator.html
├── test_do_spaces_connection.py
├── test_outputs
│   ├── character_1d0b6225-9896-433f-9703-0bc745897c60.jpg
│   ├── character_77003d37-815f-48e6-ba78-74a420ea91c7.jpg
│   ├── character_77f2b06b-e291-4439-8adc-df277869908d.jpg
│   └── character_f184bbb4-4dc5-4f96-910e-107bf4202c2c.jpg
├── utils
│   ├── __init__.py
│   └── model_manager.py
└── uv.lock

52 directories, 319 files

## Newer style
Below is an updated directory structure that accommodates the current character consistency functionality and future features (such as video generation, image slicing, lighting adjustment, background generator, image merger, etc.). I've added comments to explain the purpose of each file and folder.

project_ai_image_gen/                  # Root project folder
├── manage.py                           # Django management script
├── requirements.txt                    # Python dependencies list
├── README.md                           # Project documentation
├── celery.py                           # Celery configuration file
├── project_ai_image_gen/               # Django project settings
│   ├── __init__.py                     # Package marker
│   ├── settings.py                     # Global Django settings (including DRF, Celery, etc.)
│   ├── urls.py                         # Root URL configuration
│   ├── wsgi.py                         # WSGI application for production
│   └── asgi.py                         # ASGI application for asynchronous support
├── character_generator/                # App for generating characters
│   ├── __init__.py                     # Package marker
│   ├── admin.py                        # Django admin registration for models
│   ├── apps.py                         # App configuration
│   ├── models.py                       # Data models (e.g., Character)
│   ├── serializers.py                  # DRF serializers for input/output validation
│   ├── views.py                        # API views (endpoints for character generation)
│   ├── urls.py                         # App-specific URL configuration
│   ├── tasks.py                        # Celery tasks for asynchronous processing
│   ├── services/                       # Service layer for external API integrations
│   │   ├── __init__.py                 # Package marker
│   │   └── replicate_integration.py    # Functions to call Replicate APIs (Flux, Lora training, etc.)
│   └── tests/                          # Unit and integration tests for the app
│       ├── __init__.py                 # Package marker
│       ├── test_models.py              # Model tests
│       ├── test_views.py               # API endpoint tests
│       ├── test_services.py            # Service module tests
│       └── test_tasks.py               # Celery tasks tests
├── pose_generator/                     # App for consistent character pose generation (to be developed)
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── tasks.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── replicate_integration.py
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_views.py
│       ├── test_services.py
│       └── test_tasks.py
└── ... (other apps such as video_generator, image_processing, etc. can be added here)

