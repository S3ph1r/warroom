"""
LLM Parser Generation - First 10 Pages Sequential

Strategy:
1. Extract first 10-15 pages from PDF (contains all pattern types)
2. Ask Qwen to GENERATE the Python parser code (not extract data!)
3. Code generation is fast, data extraction is slow

This should not timeout because:
- 10-15 pages ≈ 10K chars ≈ 2500 tokens (well within context)
- Output is ~100 lines of Python code (not thousands of JSON rows)
"""
import os
import requests
import pdfplumber
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# Extract FIRST 10 pages sequentially (no manual selection)
NUM_PAGES = 10

print(f"📄 Extracting first {NUM_PAGES} pages...")
with pdfplumber.open(pdf_path) as pdf:
    pages_text = []
    for i in range(min(NUM_PAGES, len(pdf.pages))):
        text = pdf.pages[i].extract_text() or ""
        pages_text.append(f"\n=== PAGE {i+1} ===\n{text}")
    
    combined = "\n".join(pages_text)

print(f"📝 Extracted {len(combined)} chars from {NUM_PAGES} pages")

# The prompt asks for CODE GENERATION, not data extraction
PROMPT = '''You are a Python expert. Analyze this bank statement PDF structure and write a complete Python parser.

BELOW ARE THE FIRST 10 PAGES OF A BG SAXO BANK STATEMENT. Study the patterns and write Python code to extract ALL transactions.

YOUR TASK:
Write a Python function `parse_bgsaxo_pdf(pdf_path: str) -> list[dict]` that:
1. Uses pdfplumber to read the PDF
2. Extracts ALL transaction types found in these pages
3. Returns a list of dictionaries with: date, operation, name, isin, quantity, price, currency

HINTS (patterns I've observed):
- Dates look like "28-nov-2024", "19-dic-2025"
- Trades: "Contrattazione {AssetName} Acquista{qty}@{price}" or "...Vendi-{qty}@{price}"
- Deposits: "Trasferimentodiliquidità Deposito {amount}"
- Dividends: "Operazionesulcapitale {AssetName} Dividendoincontanti"
- Corporate actions: "Operazionesulcapitale" with various subtypes
- ISIN format: 2 letters + 10 alphanumeric (e.g., US1234567890)
- Amounts use Italian format: 1.234,56

IMPORTANT: 
- Return ONLY the Python code, no explanations
- The code must be COMPLETE and RUNNABLE
- Include all necessary imports
- Add a main() function that tests on a sample path

DOCUMENT PAGES:
''' + combined + '''

NOW WRITE THE COMPLETE PYTHON PARSER CODE:
'''

print(f"\n📤 Sending to Qwen (code generation, not data extraction)...")
print(f"   Prompt: {len(PROMPT)} chars")

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4000  # Enough for ~300 lines of code
        }
    },
    timeout=300  # 5 min should be plenty for code generation
)

result = response.json().get("response", "")
print(f"\n📥 Received {len(result)} chars")

# Save the generated code
out_path = Path("data/extracted/llm_parser_v2.py")
out_path.write_text(result, encoding='utf-8')
print(f"💾 Saved to: {out_path}")

# Show the code
print("\n" + "="*60)
print("GENERATED PARSER CODE:")
print("="*60)
print(result[:3000])
if len(result) > 3000:
    print(f"\n... ({len(result)-3000} more chars)")
