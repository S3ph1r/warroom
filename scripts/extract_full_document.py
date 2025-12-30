"""
Full Document LLM Extraction

Send the ENTIRE PDF text to LLM in a single request.
90K chars ≈ 23K tokens - should fit in 32K context window!
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

PROMPT_FULL_DOCUMENT = """You are a Financial Document Parser. I will give you the COMPLETE text of an 83-page bank statement from BG SAXO.

TASK: Extract ALL transactions into a JSON array.

TRANSACTION TYPES to extract:
1. "Contrattazione" with "Acquista X@Y" = BUY trade
2. "Contrattazione" with "Vendi-X@Y" = SELL trade  
3. "Trasferimento di liquidità" with "Deposito" = DEPOSIT
4. "Trasferimento di liquidità" with "Prelievo" = WITHDRAW
5. "VenditaAllachiusura" or "AcquistoInapertura" = Corporate events
6. "Dividendo" = DIVIDEND

For each transaction extract:
- date: YYYY-MM-DD format (dates appear as separators like "28-nov-2024")
- operation: BUY, SELL, DEPOSIT, WITHDRAW, DIVIDEND
- name: Asset name
- isin: ISIN code (format: 2 letters + 10 alphanumeric)
- quantity: Number (always positive)
- price: Price per unit
- total_amount: Total value
- currency: EUR, USD, CAD, etc.
- fees: Commission amount (from "Commissione" rows)

OUTPUT FORMAT (JSON only, no markdown):
{
  "transactions": [
    {"date": "2024-12-15", "operation": "BUY", "name": "NVIDIA Corp", "isin": "US67066G1040", "quantity": 10, "price": 125.50, "total_amount": 1255.00, "currency": "USD", "fees": 0.85},
    {"date": "2024-11-26", "operation": "DEPOSIT", "name": "Cash Deposit", "isin": null, "quantity": 1, "price": 1000.00, "total_amount": 1000.00, "currency": "EUR", "fees": 0}
  ]
}

DOCUMENT TEXT:
"""


def call_ollama_full(prompt):
    """Call Ollama with extended timeouts for large documents."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 16000,  # Very large output
            "num_ctx": 32768  # Max context for this model
        }
    }
    
    print(f"📤 Sending to {OLLAMA_MODEL}...")
    print(f"   Prompt length: {len(prompt)} chars")
    
    try:
        response = requests.post(url, json=payload, timeout=600)  # 10 min timeout
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
    
    # Extract ALL text from PDF
    print(f"📄 Extracting full text from: {pdf_path.name}")
    
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_text += text + "\n"
    
    print(f"📝 Total extracted: {len(all_text)} characters (~{len(all_text)//4} tokens)")
    
    # Build full prompt
    prompt = PROMPT_FULL_DOCUMENT + all_text
    
    print(f"🚀 Sending ENTIRE document to LLM...")
    print(f"   This may take 5-10 minutes with local model...")
    
    response = call_ollama_full(prompt)
    
    if not response:
        print("❌ No response!")
        return
    
    print(f"\n📥 Response received: {len(response)} chars")
    
    # Save raw response
    out_path = ROOT_DIR / "data" / "extracted" / "full_doc_response.txt"
    out_path.write_text(response, encoding='utf-8')
    print(f"💾 Saved raw response to: {out_path}")
    
    # Try to parse JSON
    import re
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        try:
            result = json.loads(match.group())
            txns = result.get('transactions', [])
            print(f"\n✅ Parsed {len(txns)} transactions!")
            
            # Operations breakdown
            from collections import Counter
            ops = Counter(t.get('operation', '?') for t in txns)
            print("\nOperations:")
            for op, count in ops.most_common():
                print(f"  {op}: {count}")
            
            # Save JSON
            json_path = ROOT_DIR / "data" / "extracted" / "BG_SAXO_Transactions_FullDoc.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved to: {json_path}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print("First 1000 chars of response:")
            print(response[:1000])
    else:
        print("❌ No JSON found in response")
        print("First 1000 chars:")
        print(response[:1000])


if __name__ == "__main__":
    main()
