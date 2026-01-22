"""
LLM Parser V4 - Template-based Prompt

Strategy: Give Qwen a CODE TEMPLATE to complete, not ask from scratch.
This way Qwen knows:
- How to use pdfplumber (template shows it)
- Where to write the parsing logic (marked with TODO)
"""
import os
import requests
import pdfplumber
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# Extract first 10 pages
print("📄 Extracting first 10 pages...")
with pdfplumber.open(pdf_path) as pdf:
    pages_text = []
    for i in range(min(10, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        pages_text.append(f"\n=== PAGE {i+1} ===\n{text}")
    combined = "\n".join(pages_text)

print(f"📝 Extracted {len(combined)} chars")

# Template-based prompt with skeleton code
PROMPT = '''Complete this Python parser. I'll give you a template with TODOs and sample PDF text.

## CODE TEMPLATE (complete the TODOs):

```python
import pdfplumber
import re
from pathlib import Path

def parse_bgsaxo_pdf(pdf_path: str) -> list:
    """Parse BG SAXO bank statement PDF."""
    transactions = []
    current_date = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split('\\n')
            
            for i, line in enumerate(lines):
                # TODO: Detect date separators (format: DD-mmm-YYYY like "28-nov-2024")
                # TODO: Look for pattern [PUT YOUR DATE REGEX HERE]
                
                # TODO: Detect TRADE transactions
                # Pattern: "Contrattazione {name} Acquista{qty}@{price}" for BUY
                # Pattern: "Contrattazione {name} Vendi-{qty}@{price}" for SELL
                # TODO: Write regex to extract name, qty, price
                
                # TODO: Detect DEPOSIT transactions
                # Pattern: "Trasferimentodiliquidità Deposito {amount}"
                # TODO: Write regex to extract amount
                
                # TODO: Extract ISIN from nearby lines
                # Pattern: 2 letters + 10 alphanumeric (e.g., US1234567890)
    
    return transactions

def main():
    pdf_path = "your_file.pdf"
    result = parse_bgsaxo_pdf(pdf_path)
    print(f"Found {len(result)} transactions")

if __name__ == "__main__":
    main()
```

## SAMPLE PDF TEXT (first 10 pages):

''' + combined + '''

## YOUR TASK:

Replace ALL the TODOs in the template above with working code.
The patterns you need to match are visible in the sample PDF text above.

Return ONLY the completed Python code, no explanations.
'''

print(f"\n📤 Sending to Qwen...")
print(f"   Prompt: {len(PROMPT)} chars")

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
print(f"\n📥 Received {len(result)} chars")

# Clean up markdown
if '```python' in result:
    result = result.split('```python')[1].split('```')[0]
elif '```' in result:
    result = result.split('```')[1].split('```')[0]

out_path = Path("data/extracted/llm_parser_v4.py")
out_path.write_text(result.strip(), encoding='utf-8')
print(f"💾 Saved to: {out_path}")

print("\n" + "="*60)
print("GENERATED CODE:")
print("="*60)
print(result[:3500])
