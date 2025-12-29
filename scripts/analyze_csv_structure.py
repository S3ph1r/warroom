
import requests
import json
import pandas as pd
import sys
from pathlib import Path

# --- CONFIG ---
OLLAMA_HOST = "http://localhost:11434"
MODEL = "qwen2.5:14b-instruct-q6_K"

PROMPT_FILE = Path(__file__).parent / "ingestion_prompts.json"

def load_prompt():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("PROMPT_CSV_RULE_DISCOVERY", "")
    except Exception as e:
        print(f"❌ Error loading prompt from {PROMPT_FILE}: {e}")
        return ""

def call_ollama(prompt):
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096}
        }
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()['response']
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None

def analyze_csv(file_path):
    print(f"[INFO] Analyzing CSV Structure: {file_path}")
    
    # Read Sample (Raw Text)
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        sample_lines = [f.readline() for _ in range(50)]
    sample_text = "".join(sample_lines)
    
    # Load Prompt
    prompt_template = load_prompt()
    if not prompt_template:
        return None
        
    # Send to LLM
    prompt = prompt_template.format(content=sample_text)
    print("   [DEBUG] PROMPT BEING SENT TO LLM:")
    print("-" * 40)
    print(prompt[:1000] + "... [TRUNCATED]" if len(prompt) > 1000 else prompt)
    print("-" * 40)
    print("   [INFO] Sending sample to LLM...")
    
    response = call_ollama(prompt)
    if not response:
        return None
        
    # Extract JSON
    try:
        # Naive JSON extraction (find first { and last })
        start = response.find('{')
        end = response.rfind('}') + 1
        json_str = response[start:end]
        config = json.loads(json_str)
        
        print("   [INFO] Received Configuration:")
        print(json.dumps(config, indent=2))
        
        # Save to file
        out_path = file_path + ".rules.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"   [INFO] Rules saved to: {out_path}")
        
        return config
    except Exception as e:
        print(f"[ERROR] Error parsing JSON response: {e}")
        print(f"Raw Response: {response}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_csv_structure.py <csv_file>")
        sys.exit(1)
        
    target_csv = sys.argv[1]
    analyze_csv(target_csv)
