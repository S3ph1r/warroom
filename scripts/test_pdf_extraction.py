"""
Test PDF Transaction Extraction - Single Page
Tests improved prompt on page 1 of BG SAXO Transactions PDF.
"""

import sys
import json
import re
import os
import requests
from pathlib import Path
import pdfplumber

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Import the prompt from main extraction script
from scripts.extract_bgsaxo_transactions import PROMPT_TRANSACTIONS, call_ollama

# IMPROVED PROMPT for Transaction Extraction
PROMPT_TRANSACTIONS = """You are a Financial Document Parser specialized in extracting stock transactions.

CRITICAL RULES:
1. The "ticker" field MUST be in format "SYMBOL:exchange" (e.g., "AAPL:xnas", "NVDA:xnys")
2. If the ticker is NOT visible, try to infer it from the ISIN code
3. Do NOT use company names as tickers
4. Extract the EXACT date from the document (format: YYYY-MM-DD)
5. Operation must be "BUY" or "SELL"
6. Quantity must be a positive number
7. Price is the per-share price

EXTRACT ALL TRANSACTIONS into this JSON format:
{{
  "transactions": [
    {{
      "date": "2024-12-15",
      "operation": "BUY",
      "ticker": "NVDA:xnas",
      "isin": "US67066G1040",
      "name": "NVIDIA Corp",
      "quantity": 10,
      "price": 125.50,
      "total_amount": 1255.00,
      "currency": "USD"
    }}
  ]
}}

DOCUMENT TEXT:
{content}

RETURN ONLY VALID JSON. No markdown, no explanation.
"""


def call_ollama(prompt, context="TEST"):
    """Call Ollama LLM."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4000
        }
    }
    
    print(f"\n[{context}] 📤 Sending to {OLLAMA_MODEL}...")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json().get("response", "")
        print(f"[{context}] 📥 Received {len(result)} chars")
        return result
    except Exception as e:
        print(f"[{context}] ❌ Error: {e}")
        return None


def parse_json_response(text):
    """Extract JSON from LLM response."""
    if not text:
        return None
    
    # Try to find JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            return {"transactions": json.loads(match.group())}
        except json.JSONDecodeError:
            pass
    
    return None


def extract_page(pdf_path, page_num=0):
    """Extract text from a single PDF page."""
    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            print(f"❌ Page {page_num} not found (PDF has {len(pdf.pages)} pages)")
            return None
        
        page = pdf.pages[page_num]
        text = page.extract_text()
        print(f"\n📄 Page {page_num + 1} extracted ({len(text)} chars)")
        print("=" * 50)
        print(text[:1000])  # First 1000 chars
        print("..." if len(text) > 1000 else "")
        print("=" * 50)
        return text


def test_extraction(pdf_path, page_num=0):
    """Test extraction on a single page."""
    print(f"🔍 Testing PDF: {pdf_path}")
    print(f"   Page: {page_num + 1}")
    
    # Extract page text
    text = extract_page(pdf_path, page_num)
    if not text:
        return
    
    # Build prompt
    prompt = PROMPT_TRANSACTIONS.format(content=text)
    
    # Call LLM
    response = call_ollama(prompt, f"PAGE_{page_num + 1}")
    
    if not response:
        print("❌ No response from LLM")
        return
    
    # Parse JSON
    result = parse_json_response(response)
    
    print("\n" + "=" * 50)
    print("📊 EXTRACTION RESULT:")
    print("=" * 50)
    
    if result and "transactions" in result:
        txns = result["transactions"]
        print(f"✅ Extracted {len(txns)} transactions")
        print()
        
        for i, t in enumerate(txns[:10], 1):
            print(f"  {i}. {t.get('date', '?')}: {t.get('operation', '?')} "
                  f"{t.get('quantity', '?')} x {t.get('ticker', '???')}")
            if t.get('isin'):
                print(f"      ISIN: {t.get('isin')}")
        
        if len(txns) > 10:
            print(f"  ... and {len(txns) - 10} more")
        
        # Save result
        out_path = ROOT_DIR / "data" / "extracted" / "test_page1_result.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to: {out_path}")
        
    else:
        print("❌ Failed to parse JSON from response")
        print("Raw response (first 500 chars):")
        print(response[:500])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, default=1, help="Page number (1-indexed)")
    args = parser.parse_args()
    
    # BG SAXO Transactions PDF
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        exit(1)
    
    test_extraction(pdf_path, page_num=args.page - 1)  # Convert to 0-indexed
