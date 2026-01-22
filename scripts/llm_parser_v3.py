"""
LLM Parser Generation V3 - Clearer Prompt

Previous issue: Qwen generated incomplete code with hardcoded text.
Solution: More explicit prompt structure with exact function signature and requirements.
"""
import os
import requests
import pdfplumber
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

NUM_PAGES = 10

print(f"📄 Extracting first {NUM_PAGES} pages...")
with pdfplumber.open(pdf_path) as pdf:
    pages_text = []
    for i in range(min(NUM_PAGES, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        pages_text.append(f"\n=== PAGE {i+1} ===\n{text}")
    combined = "\n".join(pages_text)

print(f"📝 Extracted {len(combined)} chars")

# Much clearer, more structured prompt
PROMPT = '''Generate a complete Python script to parse BG SAXO bank statement PDFs.

## REQUIREMENTS

1. Use `pdfplumber` library to read the PDF file
2. Define function: `def parse_bgsaxo_pdf(pdf_path: str) -> list[dict]`
3. Extract these transaction types:
   - TRADE: Lines starting with "Contrattazione" containing "Acquista" (BUY) or "Vendi" (SELL)
   - DEPOSIT: Lines containing "Trasferimentodiliquidità Deposito"
   - DIVIDEND: "Operazionesulcapitale" + "Dividendoincontanti"
   - CORPORATE: "Operazionesulcapitale" with other subtypes

4. For each transaction extract:
   - date: DD-MMM-YYYY format (e.g. "28-nov-2024")
   - operation: BUY, SELL, DEPOSIT, DIVIDEND, etc.
   - name: Asset name
   - isin: Pattern [A-Z]{2}[A-Z0-9]{10} from detail lines
   - quantity: Number before @ symbol
   - price: Number after @ symbol
   - currency: EUR, USD, etc.

## SAMPLE PDF TEXT (first 10 pages):

''' + combined + '''

## OUTPUT FORMAT

Return ONLY valid Python code. No explanations. The code must:
- Start with imports
- Define the parse_bgsaxo_pdf function
- Include a main() that tests the function
- Use regex for pattern matching
- Handle Italian number format (1.234,56)

```python
'''

print(f"\n📤 Sending to Qwen...")
print(f"   Prompt: {len(PROMPT)} chars")

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 5000
        }
    },
    timeout=300
)

result = response.json().get("response", "")
print(f"\n📥 Received {len(result)} chars")

# Clean up - remove markdown if present
if result.startswith('```python'):
    result = result[9:]
if result.startswith('```'):
    result = result[3:]
if result.endswith('```'):
    result = result[:-3]

# Save
out_path = Path("data/extracted/llm_parser_v3.py")
out_path.write_text(result.strip(), encoding='utf-8')
print(f"💾 Saved to: {out_path}")

print("\n" + "="*60)
print("GENERATED CODE:")
print("="*60)
print(result[:4000])
