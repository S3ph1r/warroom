"""
Full BG SAXO Transaction Extraction

1. Purges existing BG SAXO transactions
2. Extracts all pages from PDF with improved prompt
3. Loads transactions into database
"""

import sys
import json
import re
import os
import requests
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import pdfplumber
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.database import SessionLocal
from db.models import Transaction

# LLM Config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct-q6_K")

# IMPROVED PROMPT - Comprehensive for BG SAXO PDF format
PROMPT_TRANSACTIONS = """You are a Financial Document Parser for BG SAXO bank statements.

DOCUMENT FORMAT:
The document contains these transaction types which you MUST extract:
1. "Contrattazione" = Stock trade
   - "Acquista X @ Y" = BUY X shares at price Y
   - "Vendi X @ Y" = SELL X shares at price Y
2. "Trasferimento di liquidità" = Cash transfer
   - "Deposito" = DEPOSIT
   - "Prelievo" = WITHDRAW  
3. "Commissione" / "Costo" = FEE (usually shown as detail rows)
4. "Dividendo" = DIVIDEND

IMPORTANT STRUCTURE:
- Each transaction spans MULTIPLE ROWS in the PDF
- Main row contains: Tipo | Nome prodotto | Operazione | Importo
- Detail rows contain: Commissione, Valore negoziato, ISIN, ID contrattazione
- DATE appears as a BOLD separator row like "28-nov-2024" 
- Use the date from the nearest PREVIOUS date row for each transaction

TICKER RULES:
1. Format: "SYMBOL:exchange" (e.g., "NVDA:xnas", "WBD:xmil")
2. Common exchanges: xnas (NASDAQ), xnys (NYSE), xmil (Milan), xetr (Frankfurt), xhkg (Hong Kong), xcse (Copenhagen), xtsx (Toronto)
3. If you see "**See WMT:xnas (Walmart Inc.)" - extract "WMT:xnas"
4. If no ticker visible, use ISIN as identifier (e.g., "US67066G1040:isin")
5. For deposits/withdraws, use "CASH:EUR" as ticker

EXTRACT ALL TRANSACTIONS into JSON:
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
      "currency": "USD",
      "fees": 1.50
    }},
    {{
      "date": "2024-11-26",
      "operation": "DEPOSIT",
      "ticker": "CASH:EUR",
      "isin": null,
      "name": "Cash Deposit",
      "quantity": 1,
      "price": 1000.00,
      "total_amount": 1000.00,
      "currency": "EUR",
      "fees": 0
    }}
  ]
}}

DOCUMENT TEXT:
{content}

RETURN ONLY VALID JSON. Extract ALL operations including deposits, withdraws, and fees.
"""


def call_ollama(prompt, context=""):
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
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"[{context}] ❌ LLM Error: {e}")
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
    
    return None


def purge_transactions(broker):
    """Delete all transactions for a broker."""
    db = SessionLocal()
    try:
        count = db.query(Transaction).filter(Transaction.broker == broker).count()
        db.query(Transaction).filter(Transaction.broker == broker).delete()
        db.commit()
        print(f"🗑️ Purged {count} transactions for {broker}")
        return count
    finally:
        db.close()


def extract_all_pages(pdf_path, source_name):
    """Extract transactions from all PDF pages."""
    all_transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"📄 Processing {total_pages} pages...")
        
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = page.extract_text() or ""
            
            if not text.strip() or len(text) < 50:
                continue
            
            # Skip header/footer only pages - include all transaction types
            has_content = any(keyword in text for keyword in [
                "Contrattazione", "Trasferimento", "Dividendo", "Commissione",
                "Acquista", "Vendi", "Deposito", "Prelievo"
            ])
            if not has_content and page_num > 1:
                continue
            
            print(f"  📄 Page {page_num}/{total_pages}...", end=" ", flush=True)
            
            prompt = PROMPT_TRANSACTIONS.format(content=text)
            response = call_ollama(prompt, f"P{page_num}")
            
            if response:
                result = parse_json_response(response)
                if result and "transactions" in result:
                    txns = result["transactions"]
                    if txns:
                        # Add source tracking
                        for t in txns:
                            t["_source_page"] = page_num
                            t["_source_file"] = source_name
                        all_transactions.extend(txns)
                        print(f"✅ {len(txns)} txns")
                    else:
                        print("⬜ 0 txns")
                else:
                    print("⚠️ parse error")
            else:
                print("❌ no response")
            
            # Rate limiting
            time.sleep(0.5)
    
    return all_transactions


def load_to_database(transactions, broker):
    """Load transactions into database."""
    db = SessionLocal()
    loaded = 0
    errors = 0
    
    try:
        for t in transactions:
            try:
                # Parse date
                date_str = t.get("date", "")
                try:
                    txn_date = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    txn_date = datetime.now()
                
                # Create transaction
                txn = Transaction(
                    broker=broker,
                    ticker=t.get("ticker", "UNKNOWN")[:20],
                    isin=t.get("isin", "")[:12] if t.get("isin") else None,
                    operation=t.get("operation", "BUY").upper(),
                    status="COMPLETED",
                    quantity=Decimal(str(t.get("quantity", 0))),
                    price=Decimal(str(t.get("price", 0))),
                    total_amount=Decimal(str(t.get("total_amount", 0))),
                    currency=t.get("currency", "EUR")[:3],
                    timestamp=txn_date,
                    source_document=t.get("_source_file"),
                    source_page=t.get("_source_page"),
                    notes=t.get("name", "")[:200] if t.get("name") else None
                )
                db.add(txn)
                loaded += 1
                
            except Exception as e:
                errors += 1
                print(f"  ⚠️ Error loading: {e}")
        
        db.commit()
        print(f"\n✅ Loaded {loaded} transactions ({errors} errors)")
        
    finally:
        db.close()
    
    return loaded, errors


def main():
    # Config
    broker = "bgsaxo"
    pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print("=" * 60)
    print("🚀 BG SAXO FULL TRANSACTION EXTRACTION")
    print("=" * 60)
    
    # Step 1: Purge
    print("\n📋 STEP 1: Purging old transactions...")
    purge_transactions(broker)
    
    # Step 2: Extract
    print("\n📋 STEP 2: Extracting from PDF...")
    transactions = extract_all_pages(pdf_path, pdf_path.name)
    
    print(f"\n📊 Extracted {len(transactions)} total transactions")
    
    # Save intermediate result
    out_path = ROOT_DIR / "data" / "extracted" / "BG_SAXO_Transactions_Full.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": transactions}, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved to: {out_path}")
    
    # Step 3: Load to DB
    print("\n📋 STEP 3: Loading to database...")
    load_to_database(transactions, broker)
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
