# OSTRIS LORA DEV TRAINER

## About
A Cog implementation of ostris/ai-toolkit

model name owner and version = ostris/flux-dev-lora-trainer:c6e78d2501e8088876e99ef21e4460d0dc121af7a4b786b9a4c2d75c620e300d

## How to Train

Install Replicate’s Python client library:
```pip install replicate```
 
Set the REPLICATE_API_TOKEN environment variable:
```export REPLICATE_API_TOKEN=r8_2no**********************************```


This is your Default API token. Keep it to yourself.

Import the client:
```import replicate```

Train ostris/flux-dev-lora-trainer using Replicate’s API:
```python
training = replicate.trainings.create(
  # You need to create a model on Replicate that will be the destination for the trained version.
  destination="your-replicate-username/model-name"
  version="ostris/flux-dev-lora-trainer:c6e78d2501e8088876e99ef21e4460d0dc121af7a4b786b9a4c2d75c620e300d",
  input={
    "steps": 1000,
    "lora_rank": 16,
    "optimizer": "adamw8bit",
    "batch_size": 1,
    "resolution": "512,768,1024",
    "autocaption": True,
    "input_images": "https://",
    "trigger_word": "TOK",
    "learning_rate": 0.0004,
    "wandb_project": "flux_train_replicate",
    "wandb_save_interval": 100,
    "caption_dropout_rate": 0.05,
    "cache_latents_to_disk": False,
    "wandb_sample_interval": 100,
    "gradient_checkpointing": False
  },
)
```
## Parameters for Training Loras

| Parameter              | Type      | Default      | Description |
|------------------------|-----------|--------------|-------------|
| `model`                | string    | `"dev"`      | Model version or alias (optional unless needed by the backend). |
| `go_fast`              | boolean   | `False`      | If `True`, enables faster image generation at the cost of quality. |
| `lora_scale`           | float     | `1.0`        | Strength of the applied LoRA. Can be reduced or increased to adjust influence. |
| `megapixels`           | string    | `"1"`        | Approximate resolution scale. Options: `"0.5"`, `"1"`, `"2"`, `"4"`, `"8"`. |
| `num_outputs`          | integer   | `4`          | Number of images to generate in one request. |
| `aspect_ratio`         | string    | `"1:1"`      | Output image aspect ratio. Examples: `"1:1"`, `"16:9"`, `"3:4"`. |
| `output_format`        | string    | `"webp"`     | Format of the generated image. Options: `"webp"`, `"png"`, `"jpg"`. |
| `guidance_scale`       | float     | `3.0`        | Classifier-free guidance strength. Higher values make the image follow the prompt more strictly. |
| `output_quality`       | integer   | `80`         | Image quality for formats like `webp` or `jpg` (0–100). |
| `prompt_strength`      | float     | `0.8`        | Controls how strongly the prompt influences the result. Lower means more freedom. |
| `extra_lora_scale`     | float     | `1.0`        | Additional scaling for LoRA weights. Useful for layering or amplifying effects. |
| `num_inference_steps`  | integer   | `28`         | Controls the denoising steps during image generation. More steps = better quality, slower generation. |
| `prompt`               | string    | *(Required)* | The text prompt describing the image to generate. |



On replicate site, in the TRAIN tab (between README and VERSIONS) you’ll see the parameters that you can select to train a LoRA

For destination select/create an empty Replicate model location to store your LoRAs. Ex: lucataco/flux-loras)

For input_images upload your zip/tar file of images for training. File names must be their captions, ex: a_photo_of_TOK.png

For trigger_word select your training word of interest. Ex: ‘TOK’

For steps select a value from 1000-3000

The other steps are optional

Key points for Quality Flux LoRA Training Data:
Dataset Size and Image Resolution
Aim for a dataset of 12-18 images of your subject
Use high resolution images, ideally around 1024x1024 or larger, but smaller than 1440x1440
Very large images will be scaled down to fit aspect ratios around 1024 resolutions
Image selection
For style LoRAs select images that highlight distinctive features of the style, use varied subjects but keep the style consistent
For style LoRAs avoid datasets where certain elements dominate
For character LoRAs use images of the subject in different settings, facial expressions, and backgrounds.
For character LoRAs avoid different haircuts or ages, and showing hands in a lot of face framing positions as we found this led to more hand hallucinations
Training Parameter Tips
Trigger word can be a generic proper name (ex. sarah, john).
LoRA Rank between 16-32 produce good results. We’ve gone as high as 64 for likeness, and as low as 8 for styles
Increasing the step count of the inference improves LoRA coherence in the case of a weaker dataset.
The worse the dataset, the less likely that the model will be flexible enough to apply different art styles to the subject.
LoRA Inference Tips
For charater LoRAs, pair the trigger work with a gender (man, woman, etc) to improve results.
For more style LORA influence (ex: watercolor or cartoon styles) reducing the lora strength to 0.8 - 0.95 can make a difference
How to Run your Flux fine tune
After training is complete you will be able to run your LoRA in a new Replicate model at the destination location

Example Flux fine tunes
Check out some of these Flux fine tunes:

lucataco/flux-watercolor

lucataco/flux-queso

fofr/flux-pixar-cars

fofr/flux-2004

deepfates/deepfits_flux_dev

License
If you generate images on Replicate with FLUX.1 models and their fine-tunes, then you can use the images commercially.

If you download the weights off Replicate and generate images on your own computer, you can’t use the images commercially.

Off Replicate, the Flux-Dev LoRAs have the same license as the original base mode for FLUX.1-dev. If you choose the option to upload your trained LoRA to Huggingface, this License will be added for you

Create training
Trainings for this model run on Nvidia H100 GPU hardware, which costs $0.001525 per second. Upon creation, you will be redirected to the training detail page where you can monitor your training's progress, and eventually download the weights and run the trained model.

Note: versions of this model with fast booting use the hardware set by the base model they were trained from.

## Getting started
You can fine-tune FLUX.1 on Replicate by just uploading some images, either on the web or via an API.

Select a model as your destination or create a new one by typing the name in the model selector field.
Next, upload the zip file containing your training data as the input_images.
Set up the training parameters.
Learn more
↓
The trigger_word refers to the object, style or concept you are training on. Pick a string that isn’t a real word, like TOK or something related to what’s being trained, like CYBRPNK. The trigger word you specify will be associated with all images during training. Then when you run your fine-tuned model, you can include the trigger word in prompts to activate your concept.

For steps, a good starting point is 1000.

Leave the learning_rate, batch_size, and resolution at their default values. Leave autocaptioning enabled unless you want to provide your own captions.

If you want to save your model on Hugging Face, enter your Hugging Face token and set the repository ID.

Once you’ve filled out the form, click “Create training” to begin the process of fine-tuning.

Form

Python

Node.js
Destination
*
string
Select a model
Select a model on Replicate that will be the destination for the trained version. If the model does not exist, select the "Create model" option and a field will appear to enter the name of the new model. We'll create the model for you when you create the training.

input_images
*
file
Upload a compatible file (e.g. a zip) containing your training data

Upload a file from your machine
A zip file containing the images that will be used for training. We recommend a minimum of 10 images. If you include captions, include them as one .txt file per image, e.g. my-photo.jpg should have a caption file named my-photo.txt. If you don't include captions, you can use autocaptioning (enabled by default).

trigger_word
string
Shift + Return to add a new line
TOK
TOK
The trigger word refers to the object, style or concept you are training on. Pick a string that isn't a real word, like TOK or something related to what's being trained, like CYBRPNK. The trigger word you specify here will be associated with all images during training. Then when you use your LoRA, you can include the trigger word in prompts to help activate the LoRA.

Default: "TOK"


autocaption
boolean
Automatically caption images using Llava v1.5 13B

Default: true

autocaption_prefix
string
Shift + Return to add a new line
Optional: Text you want to appear at the beginning of all your generated captions; for example, 'a photo of TOK, '. You can include your trigger word in the prefix. Prefixes help set the right context for your captions, and the captioner will use this prefix as context.

autocaption_suffix
string
Shift + Return to add a new line
Optional: Text you want to appear at the end of all your generated captions; for example, ' in the style of TOK'. You can include your trigger word in suffixes. Suffixes help set the right concept for your captions, and the captioner will use this suffix as context.

steps
integer
(minimum: 3, maximum: 6000)
1000
steps
Number of training steps. Recommended range 500-4000

Default: 1000

lora_rank
integer
(minimum: 1, maximum: 128)
16
lora_rank
Higher ranks take longer to train but can capture more complex features. Caption quality is more important for higher ranks.

Default: 16

hf_repo_id
string
Shift + Return to add a new line
Hugging Face repository ID, if you'd like to upload the trained LoRA to Hugging Face. For example, lucataco/flux-dev-lora. If the given repo does not exist, a new public repo will be created.

hf_token
secret

A secret has its value redacted after being sent to the model.

Hugging Face token, if you'd like to upload the trained LoRA to Hugging Face.

wandb_api_key
secret

A secret has its value redacted after being sent to the model.

Weights and Biases API key, if you'd like to log training progress to W&B.

wandb_project
string
Shift + Return to add a new line
flux_train_replicate
flux_train_replicate
Weights and Biases project name. Only applicable if wandb_api_key is set.

Default: "flux_train_replicate"

wandb_sample_prompts
string
Shift + Return to add a new line
Newline-separated list of prompts to use when logging samples to W&B. Only applicable if wandb_api_key is set.

Showing advanced inputs
Including learning_rate and 12 more...
learning_rate
number
0.0004
Learning rate, if you're new to training you probably don't need to change this.

Default: 0.0004

batch_size
integer
1
Batch size, you can leave this as 1

Default: 1

resolution
string
Shift + Return to add a new line
512,768,1024
512,768,1024
Image resolutions for training

Default: "512,768,1024"

caption_dropout_rate
number
(minimum: 0, maximum: 1)
0.05
caption_dropout_rate
Advanced setting. Determines how often a caption is ignored. 0.05 means for 5% of all steps an image will be used without its caption. 0 means always use captions, while 1 means never use them. Dropping captions helps capture more details of an image, and can prevent over-fitting words with specific image elements. Try higher values when training a style.

Default: 0.05

optimizer
string
Shift + Return to add a new line
adamw8bit
adamw8bit
Optimizer to use for training. Supports: prodigy, adam8bit, adamw8bit, lion8bit, adam, adamw, lion, adagrad, adafactor.

Default: "adamw8bit"


cache_latents_to_disk
boolean
Use this if you have lots of input images and you hit out of memory errors

Default: false

layers_to_optimize_regex
string
Shift + Return to add a new line
Regular expression to match specific layers to optimize. Optimizing fewer layers results in shorter training times, but can also result in a weaker LoRA. For example, To target layers 7, 12, 16, 20 which seems to create good likeness with faster training (as discovered by lux in the Ostris discord, inspired by The Last Ben), use `transformer.single_transformer_blocks.(7|12|16|20).proj_out`.


gradient_checkpointing
boolean
Turn on gradient checkpointing; saves memory at the cost of training speed. Automatically enabled for batch sizes > 1.

Default: false

wandb_run
string
Shift + Return to add a new line
Weights and Biases run name. Only applicable if wandb_api_key is set.

wandb_entity
string
Shift + Return to add a new line
Weights and Biases entity name. Only applicable if wandb_api_key is set.

wandb_sample_interval
integer
(minimum: 1)
100
Step interval for sampling output images that are logged to W&B. Only applicable if wandb_api_key is set.

Default: 100

wandb_save_interval
integer
(minimum: 1)
100
Step interval for saving intermediate LoRA weights to W&B. Only applicable if wandb_api_key is set.

Default: 100

skip_training_and_use_pretrained_hf_lora_url
string
Shift + Return to add a new line
If you'd like to skip LoRA training altogether and instead create a Replicate model from a pre-trained LoRA that's on HuggingFace, use this field with a HuggingFace download URL. For example, https://huggingface.co/fofr/flux-80s-cyberpunk/resolve/main/lora.safetensors.




##  Sample Script


### Train Loras

```python
#!/usr/bin/env python3
"""
Test script for fine-tuning FLUX LoRA models using pose images
"""

import replicate
import requests
import os
import time
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv
import re
import argparse

# Load environment variables
load_dotenv()

# Set API Keys
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN environment variable is not set")
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

# Initialize Replicate client
client = replicate.Client()

# Function to get or create a model
def get_or_create_model(model_name, owner="your-replicate-username"):
    try:
        # Attempt to retrieve the existing model
        model = client.models.get(f"{owner}/{model_name}")
        print(f"✅ Using existing model: {model_name}")
        return model
    except replicate.exceptions.ReplicateError as e:
        if "404" in str(e):
            print(f"❌ Model '{model_name}' not found. Creating a new one...")
        else:
            print(f"❌ Unexpected error: {e}")
            return None

    # Create a new model if not found
    model = client.models.create(
        name=model_name,
        owner=owner,
        visibility="public",  # or "private" if preferred
        description="Fine-tuned FLUX.1 model for custom character concept",
        hardware="gpu-a100-large"
    )
    print(f"✅ New model created: {model.name}")
    print(f"🔗 Model URL: https://replicate.com/{owner}/{model.name}")
    return model

def extract_basename_from_url(url):
    """Extract base name from URL path for use as model name and trigger word"""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    
    # Find the ID in the path (typically a UUID format)
    for part in path_parts:
        # Look for UUID pattern
        if re.match(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', part):
            return part
    
    # Fallback to extracting from filename
    zip_filename = path_parts[-1]
    basename = os.path.splitext(zip_filename)[0]
    
    # If basename is empty, use a default name
    if not basename:
        import uuid
        basename = f"character-{uuid.uuid4().hex[:8]}"
    
    return basename

def download_training_data(url, output_path="./downloaded_dataset.zip"):
    """Download training data zip file from URL"""
    print(f"⏳ Downloading training data from: {url}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = downloaded / total_size * 100
                    print(f"\rDownload progress: {progress:.1f}%", end="")
        
        print("\n✅ Download complete!")
        return output_path
    except Exception as e:
        print(f"❌ Error downloading file: {str(e)}")
        return None

# Function to fine-tune the FLUX.1 model
def fine_tune_flux_model(
    training_data_url,
    model_name=None,
    trigger_word=None,
    steps=1000,
    lora_rank=16,
    learning_rate=0.0004,
    batch_size=1,
    resolution="512,768,1024",
    autocaption=True,
    optimizer="adamw8bit",
    wandb_project="flux_train_replicate",
    wandb_save_interval=100,
    caption_dropout_rate=0.05,
    cache_latents_to_disk=False,
    wandb_sample_interval=100,
    gradient_checkpointing=False,
    output_path="./downloaded_dataset.zip"
):
    """Fine-tune FLUX model using training data from URL"""
    # Extract basename from URL if model_name or trigger_word not provided
    if model_name is None or trigger_word is None:
        basename = extract_basename_from_url(training_data_url)
        model_name = model_name or basename
        trigger_word = trigger_word or basename
    
    print(f"Using model name: {model_name}")
    print(f"Using trigger word: {trigger_word}")
    
    # Get or create the model
    model = get_or_create_model(model_name)
    if model is None:
        print("❌ Model creation failed. Cannot fine-tune.")
        return None, None
    
    # Download the training data
    local_zip_path = download_training_data(training_data_url, output_path=output_path)
    if not local_zip_path or not os.path.exists(local_zip_path):
        print(f"❌ Error: Training dataset not downloaded successfully.")
        return None, None
    
    # Start the fine-tuning process
    try:
        with open(local_zip_path, "rb") as training_data:
            training = client.trainings.create(
                version="ostris/flux-dev-lora-trainer:c6e78d2501e8088876e99ef21e4460d0dc121af7a4b786b9a4c2d75c620e300d",
                destination=f"{model.owner}/{model.name}",
                input={
                    "steps": steps,
                    "lora_rank": lora_rank,
                    "optimizer": optimizer,
                    "batch_size": batch_size,
                    "resolution": resolution,
                    "autocaption": autocaption,
                    "input_images": training_data,
                    "trigger_word": trigger_word,
                    "learning_rate": learning_rate,
                    "wandb_project": wandb_project,
                    "wandb_save_interval": wandb_save_interval,
                    "caption_dropout_rate": caption_dropout_rate,
                    "cache_latents_to_disk": cache_latents_to_disk,
                    "wandb_sample_interval": wandb_sample_interval,
                    "gradient_checkpointing": gradient_checkpointing
                }
            )

        print(f"🚀 Training started: {training.status}")
        print(f"🔗 Training URL: https://replicate.com/p/{training.id}")

        # Manually poll training status until it's complete
        while True:
            updated_training = client.trainings.get(training.id)
            print(f"⏳ Training status: {updated_training.status}")

            if updated_training.status in ["succeeded", "failed", "canceled"]:
                break  # Exit loop when training is complete

            time.sleep(60)  # Wait before checking again (increased to 60 seconds)

        if updated_training.status == "succeeded":
            version = updated_training.output.get("version", "")
            print(f"✅ Training completed successfully!")
            print(f"✅ New model version: {version}")
            print(f"✅ Model can be used with trigger word: {trigger_word}")
            return model, version
        else:
            print(f"❌ Training failed: {updated_training.status}")
            if hasattr(updated_training, 'error') and updated_training.error:
                print(f"Error details: {updated_training.error}")
            return None, None
    
    except Exception as e:
        print(f"❌ Error during fine-tuning: {str(e)}")
        return None, None
    finally:
        # Clean up the downloaded file
        if os.path.exists(local_zip_path):
            os.remove(local_zip_path)
            print(f"✅ Cleaned up temporary training data")

# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune FLUX LoRA model")
    parser.add_argument("--training_data_url", "-u", required=True, help="URL to training data zip")
    parser.add_argument("--steps", "-s", type=int, default=1000, help="Number of training steps")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--optimizer", type=str, default="adamw8bit", help="Optimizer")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size")
    parser.add_argument("--resolution", type=str, default="512,768,1024", help="Image resolution")
    parser.add_argument("--autocaption", action="store_true", default=True, help="Autocaption")
    parser.add_argument("--learning_rate", type=float, default=0.0004, help="Learning rate")
    parser.add_argument("--wandb_project", type=str, default="flux_train_replicate", help="WandB project name")
    parser.add_argument("--wandb_save_interval", type=int, default=100, help="WandB save interval")
    parser.add_argument("--caption_dropout_rate", type=float, default=0.05, help="Caption dropout rate")
    parser.add_argument("--cache_latents_to_disk", action="store_true", default=False, help="Cache latents to disk")
    parser.add_argument("--wandb_sample_interval", type=int, default=100, help="WandB sample interval")
    parser.add_argument("--gradient_checkpointing", action="store_true", default=False, help="Gradient checkpointing")
    parser.add_argument("--output_path", type=str, default="./downloaded_dataset.zip", help="Output path")
    parser.add_argument("--model_name", type=str, help="Model name")
    parser.add_argument("--trigger_word", type=str, help="Trigger word")
    args = parser.parse_args()

    training_data_url = args.training_data_url
    model_name = args.model_name or extract_basename_from_url(training_data_url)
    trigger_word = args.trigger_word or extract_basename_from_url(training_data_url)

    print(f"Using training data URL: {training_data_url}")
    print(f"Model name: {model_name}")
    print(f"Trigger word: {trigger_word}")

    model, version = fine_tune_flux_model(
        training_data_url,
        model_name=model_name,
        trigger_word=trigger_word,
        steps=args.steps,
        lora_rank=args.lora_rank,
        optimizer=args.optimizer,
        batch_size=args.batch_size,
        resolution=args.resolution,
        autocaption=args.autocaption,
        learning_rate=args.learning_rate,
        wandb_project=args.wandb_project,
        wandb_save_interval=args.wandb_save_interval,
        caption_dropout_rate=args.caption_dropout_rate,
        cache_latents_to_disk=args.cache_latents_to_disk,
        wandb_sample_interval=args.wandb_sample_interval,
        gradient_checkpointing=args.gradient_checkpointing,
        output_path=args.output_path
    )

    if model and version:
        print("\n===== FINE-TUNING SUMMARY =====")
        print(f"Model name: {model.owner}/{model.name}")
        print(f"Model version: {version}")
        print(f"Trigger word to use in prompts: {trigger_word}")
        print(f"🔗 Model URL: https://replicate.com/{model.owner}/{model.name}")
        print("\nExample prompt to use with this model:")
        print(f"Ultra-detailed portrait of {trigger_word}, 8K resolution, photorealistic")
    else:
        print("\n❌ Fine-tuning process was not completed successfully.")

```


### Generate images using Trained model

We are using this model https://replicate.com/black-forest-labs/flux-1.1-pro-ultra?prediction=zx7153r8z5rma0cp6p9a3r6gd4

The payload or input for this endpoint will involve

Here's your complete input and output schema written in **Markdown table format**, suitable for copy-pasting into documentation. All details have been preserved:

---

### Input Schema

| Field                    | Type          | Default Value | Description                                                                                                                                                                                                                 |
| ------------------------ | ------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `prompt`                 | string        | –             | Prompt for generated image. If you include the `trigger_word` used in the training process you are more likely to activate the trained object, style, or concept in the resulting image.                                    |
| `image`                  | string        | –             | Input image for image-to-image or inpainting mode. If provided, `aspect_ratio`, `width`, and `height` inputs are ignored.                                                                                                   |
| `mask`                   | string        | –             | Image mask for image inpainting mode. If provided, `aspect_ratio`, `width`, and `height` inputs are ignored.                                                                                                                |
| `aspect_ratio`           | string (enum) | `1:1`         | Aspect ratio for the generated image. Options: `1:1`, `16:9`, `21:9`, `3:2`, `2:3`, `4:5`, `5:4`, `3:4`, `4:3`, `9:16`, `9:21`, `custom`. If `custom` is selected, uses `height` and `width` below & will run in bf16 mode. |
| `height`                 | integer       | –             | Height of generated image (only used if `aspect_ratio` is set to `custom`). Min: 256, Max: 1440. Will be rounded to nearest multiple of 16. Incompatible with fast generation.                                              |
| `width`                  | integer       | –             | Width of generated image (only used if `aspect_ratio` is set to `custom`). Min: 256, Max: 1440. Will be rounded to nearest multiple of 16. Incompatible with fast generation.                                               |
| `prompt_strength`        | number        | `0.8`         | Prompt strength when using img2img. Max: 1. `1.0` corresponds to full destruction of information in image.                                                                                                                  |
| `model`                  | string (enum) | `dev`         | Which model to run inference with. Options: `dev`, `schnell`. The `dev` model performs best with \~28 inference steps; the `schnell` model only needs 4 steps.                                                              |
| `num_outputs`            | integer       | `1`           | Number of outputs to generate. Min: 1, Max: 4.                                                                                                                                                                              |
| `num_inference_steps`    | integer       | `28`          | Number of denoising steps. Min: 1, Max: 50. More steps can give more detailed images but take longer.                                                                                                                       |
| `guidance_scale`         | number        | `3`           | Guidance scale for diffusion process. Max: 10. Lower values can give more realistic images. Good values to try: `2`, `2.5`, `3`, `3.5`.                                                                                     |
| `seed`                   | integer       | –             | Random seed. Set for reproducible generation.                                                                                                                                                                               |
| `output_format`          | string (enum) | `webp`        | Format of the output images. Options: `webp`, `jpg`, `png`.                                                                                                                                                                 |
| `output_quality`         | integer       | `80`          | Quality when saving output images. Max: 100. Only relevant for `webp` and `jpg`. Ignored for `png`.                                                                                                                         |
| `disable_safety_checker` | boolean       | `False`       | Disable safety checker for generated images.                                                                                                                                                                                |
| `go_fast`                | boolean       | `False`       | Run faster predictions with model optimized for speed (currently fp8 quantized); disable to run in original bf16.                                                                                                           |
| `megapixels`             | string (enum) | `1`           | Approximate number of megapixels for generated image. Options: `1`, `0.25`.                                                                                                                                                 |
| `lora_scale`             | number        | `1`           | Min: -1, Max: 3. Determines how strongly the main LoRA should be applied. For `go_fast` a 1.5x multiplier is applied. Experiment to find optimal values.                                                                    |
| `extra_lora`             | string        | –             | Load LoRA weights. Supports: Replicate `<owner>/<username>`, HuggingFace `huggingface.co/<owner>/<model-name>`, CivitAI `civitai.com/models/<id>[/<model-name>]`, or arbitrary `.safetensors` URLs.                         |
| `extra_lora_scale`       | number        | `1`           | Min: -1, Max: 3. Determines how strongly the extra LoRA should be applied. Same guidance as `lora_scale`.                                                                                                                   |

### Output Schema

| Field    | Type  | Format | Description                               |
| -------- | ----- | ------ | ----------------------------------------- |
| `output` | array | uri\[] | Array of image URLs generated by the API. |

---
 
Here is the code to generate images using the fine-tuned model. We have set the default values to match the training parameters.

```python
import replicate
import requests
import os
import json
from dotenv import load_dotenv

# Initialize the Replicate client
client = replicate.Client()

# Function to generate images using the fine-tuned model
def generate_images(model_name, model_version, prompt, num_images=4):
    print(f"🚀 Generating images using model: {model_name}:{model_version}")

    try:
        # Run the model and generate output URLs
        outputs = replicate.run(
            f"{model_name}:{model_version}",  # Use model hash
            input={
                "model": "dev",
                "go_fast": False,
                "lora_scale": 1,
                "megapixels": "1",
                "num_outputs": num_images,
                "aspect_ratio": "1:1",
                "output_format": "webp",
                "guidance_scale": 3,
                "output_quality": 80,
                "prompt_strength": 0.8,
                "extra_lora_scale": 1,
                "num_inference_steps": 28,
                "prompt": prompt  # User-provided prompt
            }
        )

        if not outputs:
            print("❌ No images generated.")
            return []

        # Download and save generated images
        image_paths = []
        for idx, img_url in enumerate(outputs):
            image_response = requests.get(img_url)
            if image_response.status_code == 200:
                image_path = f"generated_image_{idx + 1}.webp"  # Ensure correct format
                with open(image_path, "wb") as f:
                    f.write(image_response.content)
                image_paths.append(image_path)
                print(f"✅ Image saved: {image_path}")
            else:
                print(f"❌ Failed to download image {idx + 1}. Status Code: {image_response.status_code}")

        return image_paths

    except Exception as e:
        print(f"❌ Error during image generation: {e}")
        return []

# Main execution
if __name__ == "__main__":
    # Name of your fine-tuned model
    model_name = "your-replicate-username/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f" #from the model page e.g. https://replicate.com/your-replicate-username/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f

    # Model version hash (replace with your model version)
    model_version = "cb28ff88f564c9467fede8aebf088fcdcdcb51e232c7227276b5d2afdae919dc" #Copy the model details from model page https://replicate.com/your-replicate-username/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f 

    # Prompt to generate images
    trigger_word = "468cf79a-a1bf-4f4e-ac54-84aeb562ce8f"  #The last string of your model webpage https://replicate.com/your-replicate-username/468cf79a-a1bf-4f4e-ac54-84aeb562ce8f

    prompt = f"""
    Ultra-detailed, hyper-realistic scene of {trigger_word} piloting a cutting-edge Navy jet at high altitude,
    soaring through the clouds with afterburners glowing. Inside the advanced cockpit, illuminated by soft blue HUD lights,
    {trigger_word} is skillfully writing Morse code on a digital interface, glowing green signals appearing on the futuristic glass panel.
    The jet's metallic surface reflects golden sunlight, motion blur emphasizing high-speed movement.
    Aerial perspective with dynamic cinematic lighting, 8K resolution, photorealistic details,
    dramatic cloudscape, high-contrast shadows, {trigger_word}.
    """

    # Generate images
    generated_images = generate_images(model_name, model_version, prompt)

    # Display final message
    if generated_images:
        print(f"🎨 Successfully generated and saved {len(generated_images)} images.")
    else:
        print("❌ No images were generated.")

```


# Blog - Fine-tune FLUX.1 with your own images

Blog link: https://replicate.com/blog/fine-tune-flux

Posted August 15, 2024 by deepfates

FLUX.1 is a family of text-to-image models released by Black Forest Labs this summer. The FLUX.1 models set a new standard for open-source image models: they can generate realistic hands, legible text, and even the strangely hard task of funny memes.

You can now fine-tune FLUX.1 [dev] with Ostris's AI Toolkit on Replicate. Teach the model to recognize and generate new concepts by showing it a small set of example images, allowing you to customize the model's output for specific styles, characters, or objects. Ostris's toolkit uses the LoRA technique for fast, lightweight trainings.

People have already made some amazing fine-tunes:

-Generated with fofr/flux-black-light
-Generated with halimalrasihi/flux-red-cinema
-Generated with aleksa-codes/flux-ghibsky-illustration
-Generated with fofr/flux-bad-70s-food
-Generated with pixelprotest/flux-monkey-island
-Generated with pellmellism/xkcd
-Generated with shapestudio/floating-flux
-Generated with davisbrown/flux-half-illustration

## How to fine-tune FLUX.1
You can fine-tune FLUX.1 on Replicate by just uploading some images, either on the web or via an API.

If you're not familiar with Replicate, we make it easy to run AI as an API. You don't have to go looking for a beefy GPU, you don't have to deal with environments and containers, you don't have to worry about scaling. You write normal code, with normal APIs, and pay only for what you use.

Prepare your training data
To start fine-tuning, you'll need a collection of images that represent the concept you want to teach the model. These images should be diverse enough to cover different aspects of the concept. For example, if you're fine-tuning on a specific character, include images in various settings, poses, and lighting.

Here are some guidelines:

-Use 12-20 images for best results
-Use large images if possible
-Use JPEG or PNG formats
-Optionally, create a corresponding .txt file for each image with the same name, containing the caption
-Once you have your images (and optional captions), zip them up into a single file.

## Create a training on the web
To start the training process on the web, navigate to Ostris's FLUX.1 [dev] trainer on Replicate.

First, select a model as your destination or create a new one by typing the name in the model selector field.

Next, upload the zip file containing your training data as the input_images, then set up the training parameters.

The trigger_word refers to the object, style or concept you are training on. Pick a string that isn’t a real word, like TOK or something related to what’s being trained, like CYBRPNK. The trigger word you specify will be associated with all images during training. Then when you run your fine-tuned model, you can include the trigger word in prompts to activate your concept.

For steps, a good starting point is 1000.

Leave the learning_rate, batch_size, and resolution at their default values. Leave autocaptioning enabled unless you want to provide your own captions.

If you want to save your model on Hugging Face, enter your Hugging Face token and set the repository ID.

Once you've filled out the form, click "Create training" to begin the process of fine-tuning.

## Create a training via an API
Alternatively, you can create a training from your own code with an API.

Make sure you have your REPLICATE_API_TOKEN set in your environment. Find it in your account settings.

```export REPLICATE_API_TOKEN=r8_***************************```

Create a new model that will serve as the destination for your fine-tuned weights. This is where your trained model will live once the process is complete.
```python
import replicate
 
model = replicate.models.create(
    owner="yourusername",
    name="flux-your-model-name",
    visibility="public",  # or "private" if you prefer
    hardware="gpu-t4",  # Replicate will override this for fine-tuned models
    description="A fine-tuned FLUX.1 model"
)
 
print(f"Model created: {model.name}")
print(f"Model URL: https://replicate.com/{model.owner}/{model.name}")
Now that you have your model, start the training process by creating a new training run. You'll need to provide the input images, the number of steps, and any other desired parameters.

# Now use this model as the destination for your training
training = replicate.trainings.create(
    version="ostris/flux-dev-lora-trainer:4ffd32160efd92e956d39c5338a9b8fbafca58e03f791f6d8011f3e20e8ea6fa",
    input={
        "input_images": open("/path/to/your/local/training-images.zip", "rb"),
        "steps": 1000,
        "hf_token": "YOUR_HUGGING_FACE_TOKEN",  # optional
        "hf_repo_id": "YOUR_HUGGING_FACE_REPO_ID",  # optional
    },
    destination=f"{model.owner}/{model.name}"
)
 
print(f"Training started: {training.status}")
print(f"Training URL: https://replicate.com/p/{training.id}")
```

Note that it doesn't matter which hardware you pick for your model at this time, because we route to H100s for all our FLUX.1 fine-tunes. Training for this many steps typically takes 20-30 minutes and costs under $2.

## Use your trained model
Once the training is complete, you can use your trained model directly on Replicate, just like any other model.

You can run it on the web:

Go to your model page on Replicate (e.g., https://replicate.com/yourusername/flux-your-model-name).
For the prompt input, include your trigger word (such as "bad 70s food") to activate your fine-tuned concept.
Adjust any other inputs as needed.
Click "Run" to generate your image.
Or, with an API. For example, using the Python client:

```python
import replicate
 
output = replicate.run(
    "yourusername/flux-your-model-name:version_id",
    input={
        "prompt": "A portrait photo of a space station, bad 70s food",
        "num_inference_steps": 28,
        "guidance_scale": 7.5,
        "model": "dev",
    }
)
 
print(f"Generated image URL: {output}")
```

Replace yourusername/flux-your-model-name:version_id with your actual model details.

You can find more information about running it with an API on the "API" tab of your model page.

### Share your model
If you want others to be able to discover and use your new fine tuned-model, you'll need to make it public.

If you created your new model using using the web-based training form, it will be private by default.

To make your model public, go to the model settings page and set the visibility to "Public".

Once your model is public, you can share it with others by sending them the URL of the model page, and it will appear in the Explore section of the site and in the collection of Flux fine-tunes.

### Using FLUX.1 [schnell] for faster generation
You can use your FLUX.1 [dev] LoRA with the smaller FLUX.1 [schnell] model, to generate images faster and cheaper. Just change the model parameter from dev to schnell when you generate, and lower num_inference_steps to something small like 4.

Note that outputs will still be under the non-commercial license of FLUX.1 [dev].

Examples and use cases
Check out our examples gallery for inspiration. You can see how others have fine-tuned FLUX.1 to create different styles, characters, a never-ending parade of cute animals, and more.

### Base FLUX.1 model outputFine-tuned FLUX.1 model output
Left: generated with the base FLUX.1 model. Right: same prompt and seed with the model fofr/flux-bad-70s-food

### Licensing and commercial use
If you generate images on Replicate with FLUX.1 models and their fine-tunes, then you can use the images commercially.

If you download the weights off Replicate and generate images on your own computer, you can't use the images commercially.

### Pricing
You'll be billed per second for the time the training process takes to run. Trainings for the FLUX model run on Nvidia H100 GPU hardware, which costs $0.001528 per second. For a 20-minute training (which is typical when using about 20 training images and 1000 steps), you can expect to pay about $1.85 USD.

Once your model is trained, you can run it with an API just like any other Replicate model, and you'll only be billed for the time it takes to generate an image. Unlike other custom models, you won't pay for idle time on private models.

Happy training!