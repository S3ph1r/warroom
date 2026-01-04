import os
import json
import logging
import requests
import time
from pathlib import Path

# Common Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Default model, can be overridden by specific broker configs if needed
DEFAULT_MODEL = "qwen2.5:14b-instruct-q6_K"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def call_ollama(prompt, context="", model=DEFAULT_MODEL, temperature=0.0):
    """
    Generic Ollama client with logging and basic error handling.
    """
    # Visualize the Prompt
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(f"📤 PROMPT TO {model} [{context}]")
    logger.info(f"{separator}")
    logger.info(prompt)
    logger.info(f"{separator}\n")

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": temperature}
            },
            timeout=300
        )
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            logger.info(f"[{context}] 📥 RECEIVED ({len(response_text)} chars).")
            return response_text
        else:
            logger.error(f"Error calling Ollama: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Exception calling Ollama: {e}")
        return None

def parse_json_garbage(response_text):
    """
    Robust JSON extractor. Attempts to find the largest valid JSON structure
    (List or Object) inside a potentially noisy string.
    """
    if not response_text:
        return None

    # Strategy 1: Find first [ ... ] (List)
    start_list = response_text.find('[')
    end_list = response_text.rfind(']') + 1
    
    # Strategy 2: Find first { ... } (Object)
    start_obj = response_text.find('{')
    end_obj = response_text.rfind('}') + 1

    # Heuristic: Pick the one that is found and seems enclosing
    # We prefer List usually, but some prompts return Object wrapping list
    
    candidates = []
    
    if start_list != -1 and end_list > start_list:
        candidates.append((response_text[start_list:end_list], 'list'))
    
    if start_obj != -1 and end_obj > start_obj:
        candidates.append((response_text[start_obj:end_obj], 'object'))

    for snippet, form in candidates:
        try:
            data = json.loads(snippet)
            return data # Return first valid one
        except json.JSONDecodeError:
            continue
            
    return None

def save_json(data, folder, filename):
    """
    Saves data to JSON with UTF-8 encoding.
    """
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    
    path = folder / filename
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ Saved: {path}")
