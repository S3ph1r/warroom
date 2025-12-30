"""
Phase 1 v4: Sandwich Pattern Discovery Execution

This script sends the 'Sandwich Prompt' to Qwen 14B.
Goal: Get STRICT JSON Regex Rules by repeating instructions at the end.
"""
import requests
import pdfplumber
import json
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# 1. Extract Sample Text (Dense pages: 0, 1, 2, 81, 82)
print("📄 Extracting text from 5 dense pages...")
pages_to_extract = [0, 1, 2, 81, 82]
pages_text = []

with pdfplumber.open(pdf_path) as pdf:
    for p in pages_to_extract:
        if p < len(pdf.pages):
            text = pdf.pages[p].extract_text() or ""
            pages_text.append(f"--- PAGE {p+1} ---\n{text}")

sample_text = "\n".join(pages_text)

# 2. Define the Sandwich Prompt
PROMPT = f'''You are a Data Extraction Expert.
Your task is to analyze the bank statement text and generate Regex Rules in JSON format.
DO NOT WRITE A SUMMARY. WRITE ONLY JSON.

TARGET STRUCTURE:
{{
  "patterns": [
    {{
      "type": "BUY/SELL/DEPOSIT",
      "regex": "python regex pattern",
      "fields": ["amount", "currency", "etc"]
    }}
  ]
}}

PDF TEXT START:
{sample_text}
PDF TEXT END.

--------------------------------------------------------------------------------
CRITICAL INSTRUCTION:
Based on the text above, generate the JSON object defined in the TARGET STRUCTURE.
- Return ONLY valid JSON.
- No Markdown.
- No Explanations.
- No Summary.
- Start with {{ and end with }}.
--------------------------------------------------------------------------------
'''

print(f"\n📤 Sending SANDWICH prompt to Qwen ({len(PROMPT)} chars)...")

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
                # Try to stop if it starts writing markdown text
                "stop": ["```markdown", "Here is", "The regex"] 
            }
        },
        timeout=300
    )
    
    result = response.json().get("response", "")
    print(f"\n📥 Received response ({len(result)} chars)")
    
    # Clean up markdown if present
    json_str = result
    if "```json" in result:
         json_str = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
         json_str = result.split("```")[1].split("```")[0].strip()
         
    # Save raw response
    out_path = Path("data/extracted/phase1_rules_v4.json")
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
