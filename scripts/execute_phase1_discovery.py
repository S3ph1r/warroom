"""
Phase 1: Execute Pattern Discovery

This script uses the prompt strategy defined previously to ask Qwen for Regex Rules in JSON.
"""
import requests
import pdfplumber
import json
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text
print("📄 Extracting sample pages (1, 82)...")
pages_text = []
with pdfplumber.open(pdf_path) as pdf:
    for p in [1, 82]: # Page 2 and 83 (0-indexed)
        text = pdf.pages[p].extract_text() or ""
        pages_text.append(f"--- PAGE SAMPLE {p+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Prompt (Same as reviewed)
PROMPT = f'''You are a Data Extraction Expert. 
Your goal is to analyze the unstructured text from a Bank Statement PDF and define REGEX PATTERNS to extract transaction data.

We need to extract 4 types of transactions:
1. BUY (Acquisto)
2. SELL (Vendita)
3. DEPOSIT (Deposito)
4. DIVIDEND (Dividendo)

Analyze the provided TEXT SAMPLES and generate a JSON configuration with Regex patterns for each type.

The JSON structure must be exactly like this:
{{
  "common_patterns": {{
      "date": "regex to matches dates (e.g., 28-nov-2024)",
      "isin": "regex to match ISIN (e.g., US1234567890)"
  }},
  "transactions": [
    {{
      "type": "BUY",
      "start_keyword": "keyword that starts the line (e.g. Contrattazione)",
      "contains_keyword": "keyword that distinguishes this type (e.g. Acquista)",
      "regex": "regex capturing groups: name, quantity, price, currency",
      "field_map": {{ "1": "name", "2": "quantity", "3": "price", "4": "currency" }}
    }},
    {{
      "type": "SELL",
      "start_keyword": "...",
        "contains_keyword": "...",
       "regex": "...",
      "field_map": {{ ... }}
    }},
     {{
      "type": "DEPOSIT",
      "start_keyword": "...",
       "contains_keyword": "...",
      "regex": "...",
      "field_map": {{ ... }}
    }}
  ]
}}

TEXT SAMPLES:
{sample_text}

IMPORTANT: 
- Return ONLY the valid JSON.
- Regex must be Python compatible.
- Handle flexible whitespace with \s+
'''

print(f"\n📤 Sending prompt to Qwen ({len(PROMPT)} chars)...")

try:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": PROMPT,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4000}
        },
        timeout=300
    )
    
    result = response.json().get("response", "")
    print(f"\n📥 Received response ({len(result)} chars)")
    
    # Save raw response
    Path("data/extracted/phase1_rules.json").write_text(result, encoding='utf-8')
    print("💾 Saved raw response to data/extracted/phase1_rules.json")
    
    # Try to parse and pretty print
    try:
        # Extract JSON if enclosed in code blocks
        if "```json" in result:
             json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
             json_str = result.split("```")[1].split("```")[0].strip()
        else:
             json_str = result
             
        data = json.loads(json_str)
        print("\n✅ Valid JSON received!")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        print(f"\n⚠️ Response contains invalid JSON: {e}")
        print("Raw output:")
        print(result)

except Exception as e:
    print(f"\n❌ Error contacting Ollama: {e}")
