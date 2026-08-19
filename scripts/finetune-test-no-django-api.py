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