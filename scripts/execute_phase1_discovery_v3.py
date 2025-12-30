"""
Phase 1 v3: Pure Pattern Discovery Execution

This script sends the 'Pure Discovery' prompt to Qwen 14B.
Goal: Get unbiased JSON Regex Rules from the first 10 pages.
"""
import requests
import pdfplumber
import json
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (First 10 pages)
print("📄 Extracting text from first 10 pages...")
pages_text = []
with pdfplumber.open(pdf_path) as pdf:
    for i in range(10): # Pages 0-9 
        if i < len(pdf.pages):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(f"--- PAGE {i+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Prompt (Pure Discovery V3)
PROMPT = f'''You are a Data Extraction Expert.
Your task is to analyze the bank statement text below and discover the transaction patterns.

GOAL:
Identify all different transaction types (trades, deposits, fees, etc.) and create a Regex Rule for each one.

OUTPUT:
Return a JSON object with the following structure. Do NOT include any explanations.

{{
  "patterns": [
    {{
      "transaction_type": "Name of the type (e.g. BUY, SELL, DEPOSIT)",
      "trigger_keyword": "A unique word that marks the start of this transaction",
      "regex_pattern": "A generic Python regex to capture the main data (amount, name, etc.)",
      "captured_fields": ["list", "of", "field", "names"]
    }}
  ]
}}

INSTRUCTIONS:
1. Look at the text samples.
2. Find repeating structures.
3. Write GENERIC regexes (use \d+ for numbers, .*? for text).
4. Do NOT match specific company names (e.g. use generic patterns that match any company name).

PDF TEXT SAMPLES:
{sample_text}
'''

print(f"\n📤 Sending PURE DISCOVERY prompt to Qwen ({len(PROMPT)} chars)...")

try:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": PROMPT,
            "stream": False,
            "options": {
                "temperature": 0.1, 
                "num_predict": 4000,
                "stop": ["```\n", "Note:"] # Stop before it writes notes
            }
        },
        timeout=300
    )
    
    result = response.json().get("response", "")
    print(f"\n📥 Received response ({len(result)} chars)")
    
    # Clean up markdown
    json_str = result
    if "```json" in result:
         json_str = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
         json_str = result.split("```")[1].split("```")[0].strip()
         
    # Save raw response
    out_path = Path("data/extracted/phase1_rules_v3.json")
    out_path.write_text(json_str, encoding='utf-8')
    print(f"💾 Saved to: {out_path}")
    
    # Validate usage
    try:
        data = json.loads(json_str)
        print("\n✅ VALID JSON PARSED:")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        print(f"\n⚠️ Invalid JSON: {e}")
        print("Raw Content excerpt:")
        print(json_str[:500])

except Exception as e:
    print(f"\n❌ Execution Error: {e}")
