"""
LLM-Generated Parser

Strategy:
1. Extract 5 diverse sample pages from PDF (trades, deposits, corporate actions)
2. Send to Qwen with explicit request to generate a complete Python parser
3. LLM writes the parser code, we just execute it
"""
import os
import requests
import pdfplumber
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

# Sample diverse pages
SAMPLE_PAGES = [2, 6, 14, 47, 83]  # Trade, corporate action, reverse split, deposit

print("📄 Extracting sample pages...")
samples = []
with pdfplumber.open(pdf_path) as pdf:
    for p in SAMPLE_PAGES:
        text = pdf.pages[p-1].extract_text()
        samples.append(f"\n=== PAGE {p} ===\n{text}")

combined = "\n".join(samples)
print(f"📝 Extracted {len(combined)} chars from {len(SAMPLE_PAGES)} pages")

PROMPT = '''You are a Python expert. I need you to write a COMPLETE Python parser for a BG SAXO bank statement PDF.

Below are 5 SAMPLE PAGES from the PDF showing different transaction types:
- Page 2: Regular trades (Acquista = BUY, Vendi = SELL)
- Page 6: Corporate actions, rights
- Page 14: More trades  
- Page 47: Reverse stock split (Frazionamentoazionarioinverso)
- Page 83: Cash deposit (Trasferimentodiliquidità + Deposito)

YOUR TASK:
1. Analyze ALL the transaction patterns in these pages
2. Write a COMPLETE Python function that:
   - Uses pdfplumber to read the PDF
   - Extracts ALL transaction types: BUY, SELL, DEPOSIT, WITHDRAW, corporate actions (stock splits, distributions)
   - Extracts: date, operation, name, ISIN, quantity, price, currency
   - Returns a list of dictionaries

CRITICAL PATTERNS TO HANDLE:
- "Contrattazione ... Acquista X@Y" = BUY
- "Contrattazione ... Vendi-X@Y" = SELL  
- "Trasferimentodiliquidità Deposito X" = DEPOSIT
- "Operazionesulcapitale ... Frazionamentoazionarioinverso" = REVERSE_SPLIT
- "Operazionesulcapitale ... Distribuzionetitoliintermedi" = DISTRIBUTION
- Date separators look like "28-nov-2024"
- ISIN codes are on detail lines (format: 2 letters + 10 alphanumeric)

SAMPLE PAGES:
''' + combined + '''

NOW WRITE THE COMPLETE PYTHON CODE.
The code should:
1. Define a function `parse_bgsaxo_pdf(pdf_path: str) -> list[dict]`
2. Handle ALL the transaction types shown above
3. Extract ISIN for each transaction
4. Be production-ready, not a skeleton

START YOUR RESPONSE WITH THE PYTHON CODE DIRECTLY (no explanation before it).
'''

print("\n📤 Sending to Qwen...")
response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 8000}
    },
    timeout=600
)

result = response.json().get("response", "")
print(f"\n📥 Received {len(result)} chars")

# Save the generated code
out_path = Path("data/extracted/llm_generated_parser.py")
out_path.write_text(result, encoding='utf-8')
print(f"💾 Saved to: {out_path}")

# Show first part
print("\n" + "="*60)
print("GENERATED CODE (first 2000 chars):")
print("="*60)
print(result[:2000])
