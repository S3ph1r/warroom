"""
CSV Config Extractor
====================
Uses Mistral to analyze a CSV snippet and output Pandas configuration.
Mistral provides ONLY the config, then Python/Pandas does the actual parsing.
"""
import os
import sys
import json
import requests
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"  # Trying Qwen (better instruction following)

# Ultra-focused prompt - asks ONLY for Pandas config
PROMPT_PANDAS_CONFIG = """Analyze this CSV file snippet. Return ONLY the Pandas read_csv() parameters needed to parse it.

DO NOT extract or summarize the data. ONLY provide configuration.

Required output (JSON only, no text):
{{
  "pandas_config": {{
    "sep": ";",
    "header": 0,
    "encoding": "utf-8",
    "skiprows": 0
  }},
  "column_mapping": {{
    "ticker": "EXACT_COLUMN_NAME_FOR_TICKER",
    "isin": "EXACT_COLUMN_NAME_FOR_ISIN_OR_null",
    "quantity": "EXACT_COLUMN_NAME_FOR_QUANTITY",
    "currency": "EXACT_COLUMN_NAME_FOR_CURRENCY"
  }},
  "document_type": "HOLDINGS or TRANSACTIONS",
  "broker": "BROKER_NAME"
}}

Rules:
- sep: The delimiter character (look at the data, is it ";" or "," or "\\t"?)
- header: Which row (0-indexed) contains column names?
- column_mapping: Map the CSV column names to standard fields (ticker, isin, quantity, currency)
- If a column doesn't exist, use null

CSV SNIPPET:
{snippet}
"""

def read_snippet(filepath, lines=20):
    content = ""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for _ in range(lines):
            line = f.readline()
            if line:
                content += line
    return content

def call_mistral(prompt):
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=120
        )
        return resp.json().get('response', '') if resp.status_code == 200 else f"Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

def extract_json(text):
    import re
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None

def main():
    target = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv")
    
    print(f"📄 File: {target.name}")
    print("=" * 60)
    
    # Show raw snippet first
    snippet = read_snippet(target)
    print("📋 SNIPPET (first 20 lines):")
    print("-" * 40)
    print(snippet[:1500])
    print("-" * 40)
    
    # Ask Mistral
    print("\n🤖 Asking Mistral for Pandas config...")
    prompt = PROMPT_PANDAS_CONFIG.format(snippet=snippet)
    response = call_mistral(prompt)
    
    print("\n📨 RAW RESPONSE:")
    print("-" * 40)
    print(response[:2000])
    print("-" * 40)
    
    # Parse
    config = extract_json(response)
    if config:
        print("\n✅ PARSED CONFIG:")
        print(json.dumps(config, indent=2))
    else:
        print("\n❌ Could not parse JSON from response")

if __name__ == "__main__":
    main()
