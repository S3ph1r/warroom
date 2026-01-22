"""
LLM-Assisted Parser Generator

Strategy:
1. Extract text from first 4-5 pages of PDF
2. Send to LLM with request to analyze structure
3. LLM outputs Python parsing rules/code
4. Use those rules to parse entire document
"""

import sys
import os
import json
import requests
from pathlib import Path
import pdfplumber

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct-q6_K")

PROMPT_ANALYZE_STRUCTURE = """You are an expert Python developer and document parser.

I need to parse a financial PDF document from BG SAXO bank. Below is the TEXT extracted from the first 4 pages of an 83-page document.

TASK:
1. Analyze the document structure carefully
2. Identify ALL types of transactions/operations present
3. Identify the patterns/markers that indicate:
   - Start of a new transaction
   - Transaction date
   - Operation type (BUY, SELL, DEPOSIT, WITHDRAW, FEE, DIVIDEND)
   - Asset name and ticker/ISIN
   - Quantity, price, amounts
   - End of a transaction block
4. Generate Python code that can parse this document format

IMPORTANT OBSERVATIONS from screenshots:
- Each transaction type starts with keywords: "Contrattazione", "Trasferimento di liquidità"
- Dates appear as separator rows like "28-nov-2024" followed by totals
- Each main transaction has detail rows (Commissione, Valore negoziato, ISIN)
- The date for transactions is the date BEFORE them in the document flow

DOCUMENT TEXT (Pages 1-4):
{content}

YOUR RESPONSE:
1. First describe the document structure you identified
2. Then provide COMPLETE Python code with:
   - A function `parse_bgsaxo_transactions_pdf(pdf_path)` that returns a list of transaction dicts
   - Each transaction should have: date, operation, ticker, isin, name, quantity, price, total_amount, currency, fees
   - Handle all operation types: BUY, SELL, DEPOSIT, WITHDRAW, FEE, DIVIDEND

Provide your analysis and the complete Python code.
"""


def call_ollama(prompt):
    """Call Ollama LLM."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 8000  # Need more tokens for code generation
        }
    }
    
    print(f"📤 Sending to {OLLAMA_MODEL}...")
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None


def main():
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    # Extract first 4 pages
    print(f"📄 Extracting pages 1-4 from: {pdf_path.name}")
    
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(min(4, len(pdf.pages))):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(f"\n=== PAGE {i+1} ===\n{text}")
        
        # Also get last 2 pages to show full range
        for i in range(len(pdf.pages)-2, len(pdf.pages)):
            text = pdf.pages[i].extract_text() or ""
            pages_text.append(f"\n=== PAGE {i+1} (near end) ===\n{text}")
    
    combined_text = "\n".join(pages_text)
    print(f"📝 Extracted {len(combined_text)} characters from 6 pages")
    
    # Build prompt
    prompt = PROMPT_ANALYZE_STRUCTURE.format(content=combined_text)
    
    print(f"\n📤 Sending to LLM for structure analysis...")
    response = call_ollama(prompt)
    
    if not response:
        print("❌ No response from LLM")
        return
    
    print(f"\n📥 Response received ({len(response)} chars)")
    print("=" * 60)
    print(response)
    print("=" * 60)
    
    # Save response for review
    out_path = ROOT_DIR / "data" / "extracted" / "parser_rules_response.md"
    out_path.write_text(response, encoding='utf-8')
    print(f"\n💾 Saved to: {out_path}")


if __name__ == "__main__":
    main()
