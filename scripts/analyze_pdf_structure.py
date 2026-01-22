
import requests
import json
import sys
import re
from pathlib import Path
import pdfplumber

# --- CONFIG ---
PROMPT_FILE = Path(__file__).parent / "ingestion_prompts.json"
OLLAMA_HOST = "http://localhost:11434"
MODEL = "qwen2.5:14b-instruct-q6_K"

def load_prompt():
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("PROMPT_PDF_RULE_DISCOVERY", "")
    except Exception as e:
        print(f"❌ Error loading prompt: {e}")
        return ""

def call_ollama(prompt):
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 8192}
        }
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()['response']
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None

def extract_sample_text(pdf_path):
    """Extracts text from Start, Middle, and End pages to capture all transaction types."""
    print(f"[INFO] Extracting distributed sample from: {pdf_path}")
    text_sample = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Strategy: Grab 2 pages from start (skip cover), 2 from middle, 2 from end
            # Adjust indices to be safe
            start_pages = [1, 2] # Skip page 0 (usually cover)
            mid_idx = total_pages // 2
            mid_pages = [mid_idx, mid_idx + 1]
            end_pages = [total_pages - 2, total_pages - 1]
            
            # Combine and deduplicate, sort
            pages_to_read = sorted(list(set(start_pages + mid_pages + end_pages)))
            # Filter valid pages
            pages_to_read = [p for p in pages_to_read if 0 <= p < total_pages]
            
            print(f"   Reading pages: {pages_to_read}")
            
            for p_idx in pages_to_read:
                page = pdf.pages[p_idx]
                page_text = page.extract_text()
                if page_text:
                    text_sample += f"\n--- PAGE {p_idx} START ---\n"
                    text_sample += page_text
                    text_sample += f"\n--- PAGE {p_idx} END ---\n"
                    
    except Exception as e:
        print(f"[ERROR] PDF Read Error: {e}")
        return None
        
    return text_sample

def extract_json_block(text):
    """Extracts JSON using regex for code blocks or brace matching."""
    # 1. Try Markdown Code Block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
            
    # 2. Try Brace Matching (First { to Last })
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except:
        pass
        
    return None

def main(pdf_path):
    print("[INFO] Analyzing PDF Structure...")
    
    # 1. Extract Text
    content = extract_sample_text(pdf_path)
    if not content:
        sys.exit(1)
        
    prompt_template = load_prompt()
    if not prompt_template:
        print("[ERROR] Prompt not found in JSON.")
        sys.exit(1)

    prompt = prompt_template.replace("{content}", content)

    print("   [DEBUG] PROMPT BEING SENT TO LLM:")
    print("-" * 40)
    print(prompt[:1500] + "... [TRUNCATED]" if len(prompt) > 1500 else prompt)
    print("-" * 40)

    # 2. Ask LLM
    print("   [INFO] Sending sample to LLM...")
    response = call_ollama(prompt)
    
    if not response:
        print("[ERROR] No response from LLM")
        sys.exit(1)

    # 3. Parse JSON
    config = None
    try:
        # Try direct parse
        config = json.loads(response)
    except json.JSONDecodeError:
        print("   [WARN] Raw JSON parse failed, trying to extract block...")
        config = extract_json_block(response)
        
    if not config:
        print(f"[ERROR] Error parsing JSON response. Raw:\n{response[:200]}...")
        sys.exit(1)
        
    print("   [INFO] Received Configuration:")
    # print(json.dumps(config, indent=2))
    
    # 4. Save
    out_path = pdf_path + ".rules.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"   [INFO] Rules saved to: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf_structure.py <pdf_file>")
        sys.exit(1)
        
    main(sys.argv[1])
