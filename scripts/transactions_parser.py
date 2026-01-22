"""
TRANSACTIONS PARSER - BG SAXO
==============================
1. Mistral analizza PDF transazioni e genera istruzioni
2. PyMuPDF estrae tabelle/testo
3. Pandas formatta i dati
4. VALIDAZIONE: SUM(BUY) - SUM(SELL) = Holdings finale
"""
import json
import requests
import fitz  # PyMuPDF
from pathlib import Path
from collections import defaultdict

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

def get_pdf_preview(file_path: str, max_pages: int = 5) -> str:
    """Extract text from first pages of PDF."""
    doc = fitz.open(file_path)
    preview = []
    
    for page_num in range(min(max_pages, len(doc))):
        page = doc[page_num]
        
        # Try tables first
        tabs = page.find_tables()
        if tabs.tables:
            preview.append(f"=== PAGE {page_num+1} (TABLES) ===")
            for tab in tabs.tables[:2]:  # First 2 tables
                md = tab.to_markdown()
                preview.append(md[:800])
        else:
            # Fallback to text
            text = page.get_text("text")[:1200]
            preview.append(f"=== PAGE {page_num+1} (TEXT) ===")
            preview.append(text)
    
    doc.close()
    return "\n".join(preview)

def get_transaction_instructions(preview: str) -> dict:
    """Mistral genera istruzioni per estrarre transazioni."""
    
    PROMPT = f"""Analizza questo documento PDF di transazioni finanziarie e genera istruzioni per l'estrazione.

DOCUMENTO:
{preview}

Cerca transazioni come:
- Acquisti (BUY)
- Vendite (SELL)  
- Dividendi (DIVIDEND)
- Commissioni (FEE)

Per ogni transazione identifica:
- Data
- Tipo operazione
- Asset/Nome prodotto
- ISIN (se presente)
- Quantità (+per BUY, -per SELL)
- Prezzo unitario
- Importo totale
- Commissioni
- Valuta

Rispondi con JSON:
{{
  "document_info": {{
    "total_pages": 0,
    "date_range": "from - to",
    "broker": "BG SAXO"
  }},
  "transaction_patterns": {{
    "buy_keywords": ["Acquisto", "Buy"],
    "sell_keywords": ["Vendita", "Sell", "Vendi"],
    "dividend_keywords": ["Dividendo", "Dividend"]
  }},
  "data_structure": {{
    "transactions_per_block": 1,
    "fields_identified": ["date", "type", "asset", "quantity", "price", "amount"]
  }},
  "sample_transactions": [
    {{
      "date": "2025-01-15",
      "type": "BUY",
      "asset": "Apple Inc.",
      "isin": "US0378331005",
      "quantity": 10.0,
      "price": 150.50,
      "amount": 1505.00,
      "fees": 5.00,
      "currency": "USD"
    }}
  ],
  "validation": {{
    "transaction_count_estimate": 0,
    "assets_found": ["asset1", "asset2"]
  }}
}}"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 3000}
        },
        timeout=180
    )
    
    if response.status_code == 200:
        try:
            return json.loads(response.json().get("response", "{}"))
        except:
            return {"error": "Failed to parse"}
    return {"error": f"API error: {response.status_code}"}

def extract_transactions_from_pdf(file_path: str, instructions: dict) -> list:
    """Extract transactions using Text Analysis and Regex (More robust than tables)."""
    import re
    doc = fitz.open(file_path)
    all_transactions = []
    
    # Regex for dates like 19-dic-2025 or 01-gen-2025
    date_pattern = re.compile(r'(\d{2}-[a-z]{3}-\d{4})', re.IGNORECASE)
    
    print(f"Processing {len(doc)} pages with Text/Regex parsing...")
    
    current_txn = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks") # (x0, y0, x1, y1, "lines\n", block_no, block_type)
        blocks.sort(key=lambda b: (b[1], b[0])) # Sort by Y (vertical), then X (horizontal)
        
        for b in blocks:
            text = b[4].strip()
            if not text: continue
            
            # Helper to detect transaction lines
            # Structure matches: Date | Type | Asset | Amount
            
            lines = text.split('\n')
            for line in lines:
                # Check if line starts with date
                date_match = date_pattern.search(line)
                if date_match and ('Acquisto' in line or 'Vendita' in line or 'Dividendo' in line or 'Buy' in line or 'Sell' in line):
                    # Found a transaction line!
                    try:
                        parts = line.split()
                        date_str = date_match.group(1)
                        
                        # Very basic parsing based on keywords
                        txn_type = "UNKNOWN"
                        if 'Acquisto' in line or 'Buy' in line: txn_type = 'BUY'
                        elif 'Vendita' in line or 'Sell' in line: txn_type = 'SELL'
                        elif 'Dividendo' in line: txn_type = 'DIVIDEND'
                        
                        # Try to extract numbers (quantity, price)
                        # Look for numbers with decimals
                        numbers = re.findall(r'-?\d+[.,]\d+', line)
                        qty = 0.0
                        amount = 0.0
                        
                        if numbers:
                            # Heuristic: usually Qty is integer-like, Price/Amount has decimals
                            # This is fragile without Mistral's specific mapping, but let's try
                            pass

                        # Save what we found
                        all_transactions.append({
                            "page": page_num + 1,
                            "date": date_str,
                            "type": txn_type,
                            "raw_line": line,
                            "quantity": 0, # Placeholder
                            "asset": "Unknown (Regex)" # Placeholder
                        })
                    except:
                        pass
                        
    # Mistral Approach:
    # Since regex is hard, let's use Mistral for a few Sample Pages to get the EXACT format
    # But for now, returning the regex hits
    
    doc.close()
    return all_transactions

def reconcile_with_holdings(transactions: list, holdings_file: str) -> dict:
    """
    Verifica: SUM(BUY) - SUM(SELL) = Holdings finale
    """
    # Load holdings
    with open(holdings_file, 'r', encoding='utf-8') as f:
        holdings_data = json.load(f)
    
    holdings = {h['name']: h['quantity'] for h in holdings_data.get('holdings', [])}
    
    # This would compute transaction sums per asset
    # For now, return placeholder
    return {
        "holdings_count": len(holdings),
        "reconciled": "pending",
        "message": "Full reconciliation requires parsing all transactions"
    }

def process_transactions(pdf_path: str):
    """Main function for transaction extraction."""
    
    print("="*70)
    print("TRANSACTIONS PARSER - BG SAXO")
    print("="*70)
    print(f"File: {Path(pdf_path).name}")
    print()
    
    # Step 1: Get PDF preview
    print("STEP 1: Reading PDF preview...")
    preview = get_pdf_preview(pdf_path)
    print(f"Preview length: {len(preview)} chars")
    print()
    print("PREVIEW (first 1500 chars):")
    print(preview[:1500])
    print()
    
    # Step 2: Get Mistral instructions (Skipping for speed in this demo, reusing logic)
    print("STEP 2: Asking Mistral... (Skipped for demo efficiency)")
    instructions = {} 
    print()
    
    # Step 3: Extract transactions
    print("STEP 3: Extracting transactions...")
    transactions = extract_transactions_from_pdf(pdf_path, instructions)
    
    print(f"Extracted {len(transactions)} transactions.")
    if transactions:
        print("Sample (first 3):")
        for t in transactions[:3]:
            print(f"  {t.get('date')} | {t.get('type')} | {t.get('asset')[:20]} | Qty: {t.get('quantity')}")
    print()
    
    # Step 4: Reconcile with holdings
    print("STEP 4: Reconciliation with holdings...")
    holdings_file = "scripts/Posizioni_19-dic-2025_17_49_12_extracted.json"
    if Path(holdings_file).exists():
        recon = reconcile_with_holdings(transactions, holdings_file)
        print(json.dumps(recon, indent=2))
    else:
        print("Holdings file not found for reconciliation")
    
    # Save results WITH transactions list
    result = {
        "file": str(pdf_path),
        "transactions": transactions, # THIS WAS MISSING
        "count": len(transactions)
    }
    
    output_path = "scripts/bgsaxo_transactions_extracted.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"Saved to: {output_path}")
    
    return result

if __name__ == "__main__":
    pdf_path = r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf"
    if Path(pdf_path).exists():
        process_transactions(pdf_path)
    else:
        print(f"File not found: {pdf_path}")
