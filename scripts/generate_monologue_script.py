#!/usr/bin/env python3
"""
Generates a podcast monologue script using the configured LLM provider
(LLM_PROVIDER env var — see shared/providers/llm/factory.py; defaults to
OpenRouter for backward compatibility).

This script takes a prompt, speaker name, and an optional PDF file to generate a
monologue. The output is saved as a text file and a JSON file.

Example:
  python scripts/generate_monologue_script.py \
      --project-name "My Podcast" \
      --prompt "An introduction to quantum computing" \
      --speaker-name "Dr. Evelyn Reed" \
      --script-number 1
"""

import os
import sys
import argparse
import json
import requests
from dotenv import load_dotenv

# Allow `from shared.providers.llm import get_llm_provider` without Django,
# matching the sys.path convention used by the other standalone scripts here.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.providers.llm import get_llm_provider

# Attempt to import PyPDF2, provide instructions if not found
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Load environment variables
load_dotenv()
load_dotenv('.env-do')

def generate_script(prompt, speaker_name, pdf_content=None):
    """Generates a script using the configured LLM provider (LLM_PROVIDER env var; defaults to OpenRouter)."""
    full_prompt = f"Create a podcast monologue script for a speaker named {speaker_name}.\n"
    full_prompt += f"The topic is: {prompt}\n"

    if pdf_content:
        full_prompt += f"\nUse the following content as a reference:\n{pdf_content}\n"

    full_prompt += "\nPlease provide the output in two formats inside a single JSON object:\n"
    full_prompt += "1. A 'text_script' field containing the full monologue as a single string.\n"
    full_prompt += "2. A 'json_script' field which is an array of objects, where each object has 'speaker', 'sentence', and 'expression' keys. the values of 'expression' has to be either 'auto', 'neutral', 'happy', 'sad','angry','fearful','disgusted' or 'surprised'\n"

    try:
        provider = get_llm_provider()
        completion = provider.chat([{"role": "user", "content": full_prompt}])

        # Clean the completion string: remove markdown fences and trim whitespace
        if completion.strip().startswith("```json"):
            completion = completion.strip()[7:-3].strip()
        elif completion.strip().startswith("```"):
            completion = completion.strip()[3:-3].strip()

        # The response from the LLM should be a JSON string, so we parse it.
        script_data = json.loads(completion)
        return script_data

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response: {e}")
        print(f"Raw completion: {completion}")
        return None
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error calling LLM provider: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing LLM response: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    if not PyPDF2:
        print("PyPDF2 library is not installed. Please run 'pip install PyPDF2' to handle PDF files.")
        return None
    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error reading PDF file {pdf_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate a podcast monologue script.")
    parser.add_argument("--project-name", required=True, help="The name of the project.")
    parser.add_argument("--prompt", required=True, help="The prompt for the monologue.")
    parser.add_argument("--speaker-name", required=True, help="The name of the speaker.")
    parser.add_argument("--pdf-file", help="Path to an optional PDF file for context.")
    parser.add_argument("--save-location", default="./media", help="Directory to save the output files.")
    parser.add_argument("--script-number", type=int, default=1, help="The script number.")
    args = parser.parse_args()

    pdf_content = None
    if args.pdf_file:
        print(f"Extracting text from PDF: {args.pdf_file}")
        pdf_content = extract_text_from_pdf(args.pdf_file)
        if not pdf_content:
            print("Could not extract text from PDF. Continuing without PDF context.")

    script_data = generate_script(args.prompt, args.speaker_name, pdf_content)

    if script_data:
        # Validate expression values
        allowed_expr = {"auto", "neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"}
        json_list = script_data.get('json_script', [])
        for item in json_list:
            expr = str(item.get('expression', 'auto')).lower().strip()
            if expr not in allowed_expr:
                expr = 'auto'
            item['expression'] = expr

        # Update script_data with cleaned list
        script_data['json_script'] = json_list

        os.makedirs(args.save_location, exist_ok=True)

        # Sanitize parts for filename, replacing spaces with dashes
        project_name = args.project_name.replace(' ', '-')
        speaker_name = args.speaker_name.replace(' ', '-')

        # Create base filename
        base_filename = f"{project_name}-{speaker_name}-monologue-{args.script_number}"

        # Save the text script
        text_script_path = os.path.join(args.save_location, f"{base_filename}.txt")
        with open(text_script_path, "w") as f:
            f.write(script_data.get('text_script', ''))
        print(f"Text script saved to {text_script_path}")

        # Save the JSON script
        json_script_path = os.path.join(args.save_location, f"{base_filename}.json")
        with open(json_script_path, "w") as f:
            json.dump(script_data.get('json_script', []), f, indent=2)
        print(f"JSON script saved to {json_script_path}")

if __name__ == "__main__":
    main()
