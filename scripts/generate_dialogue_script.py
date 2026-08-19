import os
import sys
import json
import argparse
import requests
import PyPDF2
from dotenv import load_dotenv
import logging

# Allow `from shared.providers.llm import get_llm_provider` without Django,
# matching the sys.path convention used by the other standalone scripts here.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.providers.llm import get_llm_provider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "".join(page.extract_text() for page in reader.pages)
        return text
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path}: {e}")
        return None

def generate_script(prompt, speaker_names, context=None):
    """Generates a dialogue script using the configured LLM provider (LLM_PROVIDER env var; defaults to OpenRouter)."""
    full_prompt = f"{prompt}\n\nSpeakers: {', '.join(speaker_names)}\n\nHere is some additional context:\n\n{context}"

    messages = [
        {"role": "system", "content": "You are a scriptwriter. Create a compelling dialogue for a podcast with the specified speakers. The output should be just the script content, in the format 'Speaker Name: Dialogue line'. Each line of dialogue should be on a new line."},
        {"role": "user", "content": full_prompt},
    ]

    try:
        provider = get_llm_provider()
        return provider.chat(messages, temperature=0.8, max_tokens=3000)
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"LLM provider request failed: {e}")
        return None

def analyze_sentiment(sentence):
    """Analyzes the sentiment of a sentence using a simple keyword-based approach."""
    if any(word in sentence.lower() for word in ["excited", "amazing", "wonderful"]):
        return "excited"
    if any(word in sentence.lower() for word in ["sad", "unfortunately", "sorry"]):
        return "sad"
    if any(word in sentence.lower() for word in ["angry", "frustrated"]):
        return "angry"
    return "neutral"

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a dialogue podcast script.")
    parser.add_argument("--prompt", required=True, help="The prompt to generate the script from.")
    parser.add_argument("--pdf", help="Path to a PDF file for additional context.")
    parser.add_argument("--speaker_names", required=True, nargs='+', help="Names of the speakers.")
    parser.add_argument("--speaker_ids", required=True, nargs='+', help="IDs of the speakers.")
    parser.add_argument("--output_dir", default="./media/output/scripts", help="Directory to save the output files.")

    args = parser.parse_args(argv)

    if len(args.speaker_names) != len(args.speaker_ids):
        raise ValueError("The number of speaker names must match the number of speaker IDs.")

    os.makedirs(args.output_dir, exist_ok=True)

    context = ""
    if args.pdf:
        logging.info(f"Extracting text from {args.pdf}...")
        context = extract_text_from_pdf(args.pdf)
        if not context:
            logging.error("Could not extract text from PDF. Exiting.")
            return

    logging.info("Generating script...")
    script_text = generate_script(args.prompt, args.speaker_names, context)

    if not script_text:
        logging.error("Failed to generate script. Exiting.")
        return

    base_name = args.prompt.lower().replace(" ", "_")[:20]
    text_file = os.path.join(args.output_dir, f"{base_name}_dialogue.txt")
    json_file = os.path.join(args.output_dir, f"{base_name}_dialogue.json")

    with open(text_file, 'w') as f:
        f.write(script_text)
    logging.info(f"Script saved to {text_file}")

    lines = [s.strip() for s in script_text.split('\n') if s.strip() and ':' in s]
    lines_data = []
    speaker_map = {name: id for name, id in zip(args.speaker_names, args.speaker_ids)}

    for line in lines:
        try:
            speaker_name, dialogue = line.split(':', 1)
            speaker_name = speaker_name.strip()
            dialogue = dialogue.strip()
            if speaker_name in speaker_map:
                lines_data.append({
                    "speaker_name": speaker_name,
                    "speaker_id": speaker_map[speaker_name],
                    "line": dialogue,
                    "sentiment/expression": analyze_sentiment(dialogue)
                })
        except ValueError:
            logging.warning(f"Could not parse line: {line}")

    script_json_object = {
        "full_script": "\n".join(lines),
        "lines": lines_data
    }

    with open(json_file, 'w') as f:
        json.dump(script_json_object, f, indent=4)
    logging.info(f"JSON output saved to {json_file}")

    return json_file

if __name__ == "__main__":
    main()
