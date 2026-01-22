"""
FULL TRANSACTIONS EXTRACTOR - BG SAXO (75 Pages)
================================================
Iterates through every page of the transaction PDF.
Uses Mistral to extract structured data from complex text blocks.
Saves progress incrementally.
"""
import json
import requests
import fitz  # PyMuPDF
import time
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"
PDF_PATH = r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf"
OUTPUT_FILE = "scripts/bgsaxo_transactions_full.json"

def extract_page(page_text, page_num):
    """Ask Mistral to extract transactions from a single page text."""
    PROMPT = f"""Sei un data entry specialist preciso. Estrai le transazioni finanziarie da questo testo.

TESTO PAGINA {page_num}:
{page_text}

ISTRUZIONI:
1. Ignora intestazioni, piè di pagina e saldi riportati.
2. Cerca SOLO blocchi di eventi: Acquisto, Vendita, Dividendo, Deposito, Prelievo.
3. Per ogni evento estrai:
   - date: Data operazione (YYYY-MM-DD)
   - type: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FEE
   - asset: Nome dello strumento (es. Qualcomm, Canopy Growth)
   - isin: Codice ISIN se presente
   - quantity: Numero azioni (negativo per vendita)
   - amount: Importo netto in EUR
   - currency: Valuta originale (es. USD, CAD)

Rispondi SOLO con
    - For "Account Statement" or "PnL" documents:
      If a row has BOTH "Date Acquired" and "Date Sold" (or similar):
      Create TWO transaction objects.
    
    - For Revolut Trading/Account Statements:
      - Look for "XAU" (Gold) and "XAG" (Silver).
      - "Scambio da EUR a XAU" -> BUY XAU.
      - "Scambio da XAU a EUR" -> SELL XAU.
      - "Exchange to XAU" -> BUY XAU.
      - "Gold" or "Silver" may be used as Asset Name.
      - Look for: "AMZN Trade - Market ... 2 ... US$121.14 Buy US$243.30"
      - Or: "INTC Dividend ... US$1.56"
      - Extract:
        - Date: From timestamp line (e.g. "25 Jul 2022")
        - Asset: Symbol (e.g. "AMZN", "XAU", "XAG")
        - Type: "BUY" or "SELL" (from "Buy/Sell" text) or "DIVIDEND"
        - Quantity: Number (e.g. 2, 0.5)
        - Amount: Value (e.g. 243.30). Make Cost negative.
        
    - For Trade Republic (Italian/English mixed):
      - "Buy trade [ISIN] [Name], quantity: [N]" -> BUY.
      - "Cash Dividend for ISIN [ISIN]" -> DIVIDEND.
      - "Sell trade ..." -> SELL.
      - Dates: "22 gencio" -> 22 Jan. "febcio" -> Feb. "mar" -> Mar. 
      - Extract:
        - Date: Combine Day/Month with nearest Year (e.g. 2024 line above).
        - Asset: Name (e.g. "ALIBABA GROUP").
        - ISIN: (e.g. KYG017191142).
        - Quantity: From "quantity: X".
        - Amount: The EUR value associated. Custody fees are negative.
        
    - OUTPUT FORMAT: JSON list of objects.
    - {{
        "date": "YYYY-MM-DD",
        "type": "BUY/SELL/DIVIDEND/FEE/TAX",
        "asset": "Name of stock/ETF",
        "isin": "ISIN if available",
        "quantity": 10.0,
        "amount": 1000.00,
        "currency": "EUR/USD"
       }}
Se non ci sono transazioni, restituisci: {{"transactions": []}}"""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": PROMPT,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 2048} # Faster generation
            },
            timeout=60
        )
        if response.status_code == 200:
            return json.loads(response.json().get("response", "{}")).get("transactions", [])
    except Exception as e:
        print(f"Error extracting page {page_num}: {e}")
    return []

def run_extraction(pdf_path, output_file):
    print(f"Opening {pdf_path}...")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")
    
    all_transactions = []
    
    # Check for existing partial progress
    if Path(output_file).exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
            # Only resume if source matches
            if saved.get('source') == str(pdf_path):
                all_transactions = saved.get('transactions', [])
                start_page = saved.get('last_processed_page', 0) + 1
                print(f"Resuming from page {start_page} (Loaded {len(all_transactions)} txns)")
            else:
                start_page = 0
    else:
        start_page = 0

    MAX_PAGES_PER_RUN = 100 
    end_page = min(start_page + MAX_PAGES_PER_RUN, total_pages)
    
    print(f"Processing pages {start_page} to {end_page-1}...")
    
    for i in range(start_page, end_page):
        page = doc[i]
        # Sort blocks by Y (vertical), then X (horizontal) to ensure reading order
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        text = "\n".join([b[4] for b in blocks])
        
        # Debug: Print a snippet
        # print(f"DEBUG PAGE TEXT: {text[:200]}")
        
        # Skip empty pages or cover pages heuristics
        if len(text) < 100 or "Pagina" not in text and "Page" not in text: # Added "Page" for English docs
            # print(f"Page {i+1}: Skipped (Low content)")
            pass
            
        print(f"Page {i+1}: Extracting...", end="", flush=True)
        t0 = time.time()
        txns = extract_page(text, i+1)
        print(f" Found {len(txns)} txns ({time.time()-t0:.1f}s)")
        
        all_transactions.extend(txns)
        
        # Save progress every page
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "source": str(pdf_path),
                "last_processed_page": i,
                "total_pages": total_pages,
                "transactions": all_transactions
            }, f, indent=2, ensure_ascii=False)

    print("-" * 50)
    print(f"Extraction Batch Complete.")
    print(f"Total Transactions Extracted: {len(all_transactions)}")
    
    return all_transactions

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="Path to input PDF", required=False)
    parser.add_argument("--output", help="Path to output JSON", required=False)
    args = parser.parse_args()
    
    # Defaults (BG Saxo) if no args provided
    default_path = r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf"
    default_out = "scripts/bgsaxo_transactions_full.json"
    
    if args.pdf and args.output:
        run_extraction(args.pdf, args.output)
    elif Path(default_path).exists():
        print("No args provided. Using default BG Saxo path.")
        run_extraction(default_path, default_out)
    else:
        print("Please provide --pdf and --output arguments.")
