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
