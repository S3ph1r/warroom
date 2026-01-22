import sys
from pathlib import Path
import pdfplumber
import time

# Add parent dir to path to import lib
sys.path.append(str(Path(__file__).resolve().parent.parent))
from ingestion_lib import call_ollama, parse_json_garbage, save_json

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'extracted' / 'bgsaxo'

# =============================================================================
# PROMPTS (BG SAXO SPECIFIC)
# =============================================================================

PROMPT_CSV_BGSAXO = """You are a Data Processor reading a BG SAXO Portfolio CSV.
Convert this CSV segment into a JSON array.

COLUMNS USUALLY FOUND:
- "Strumento": Name/Ticker
- "Quantità": Quantity
- "Prezzo apertura": Average Cost (Cost Basis)
- "Prezzo corrente": Market Price
- "Valuta": Currency (EUR/USD/etc)
- "ISIN": ISIN Code

INSTRUCTIONS:
1. Analyze the content.
2. Identify document_type="HOLDING" (since this is a Portfolio snapshot).
3. Map columns to: ticker, name, isin, quantity, price (current), currency.
4. Return a JSON list.

RULES:
- Return ONLY valid JSON (List).
- Ignore summary/garbage lines like "Azioni (48)" or "Totale portafoglio".

CSV CONTENT:
{content}
"""

PROMPT_PDF_BGSAXO = """You are a Financial Data Extractor reading a BG SAXO Transaction Report.
Analyze the text below.

DOCUMENT TYPE:
If it lists assets with 'Prezzo' and 'Valore', it's HOLDINGS.
If it lists 'Data', 'Operazione' (Buy/Sell), 'Importo', it's TRANSACTIONS.

TASK:
Extract the data into a JSON structure.

IF TRANSACTIONS:
- date (YYYY-MM-DD): The date of trade.
- type: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW.
- ticker: The Symbol or Name.
- isin: The ISIN code if present.
- quantity: Number of shares (negative for sell).
- price: Execution price.
- total_amount: Net amount (negative for buy outlfow, positive for sell inflow).
- currency: Currency of the amount.

RETURN JSON:
{{
  "document_type": "TRANSACTIONS",
  "data": [ ... ]
}}

DOCUMENT TEXT:
{content}
"""

# =============================================================================
# LOGIC
# =============================================================================

def run(files):
    """
    Main entry point for BG SAXO.
    Files: List of Path objects.
    """
    print(f"🔹 Starting BG SAXO Extraction on {len(files)} files...")
    
    for f in files:
        ext = f.suffix.lower()
        if ext == '.csv':
            process_csv(f)
        elif ext == '.pdf':
            process_pdf(f)
        else:
            print(f"Skipping {f.name} (unsupported)")

def process_csv(filepath):
    print(f"   --> Processing CSV: {filepath.name}")
    chunk_size = 10
    all_items = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        if not lines: return

        header_line = lines[0].strip()
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i : i + chunk_size]
            
            # Context builder
            if i == 0:
                content = "".join(chunk_lines)
            else:
                content = header_line + "\n" + "".join(chunk_lines)
            
            prompt = PROMPT_CSV_BGSAXO.format(content=content)
            response = call_ollama(prompt, context=f"BGSAXO_CSV_{i}", temperature=0.0)
            
            if response:
                data = parse_json_garbage(response)
                # Helper allows list or object wrapping list
                if isinstance(data, list):
                    all_items.extend(data)
                elif isinstance(data, dict):
                    # Try finding list inside
                    for k in ['data', 'holdings', 'items']:
                        if k in data and isinstance(data[k], list):
                            all_items.extend(data[k])
            
            # time.sleep(0.5)

    except Exception as e:
        print(f"Error csv {filepath.name}: {e}")

    # Save
    if all_items:
        save_json({
            "broker": "bgsaxo",
            "source_file": filepath.name,
            "data": all_items
        }, OUTPUT_DIR, f"{filepath.name}.json")


def process_pdf(filepath):
    print(f"   --> Processing PDF: {filepath.name}")
    all_items = []
    doc_type = "UNKNOWN"
    
    try:
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                
                print(f"       Page {i+1}...")
                prompt = PROMPT_PDF_BGSAXO.format(content=text)
                response = call_ollama(prompt, context=f"BGSAXO_PDF_{i}", temperature=0.0)
                
                if response:
                    data = parse_json_garbage(response)
                    if isinstance(data, dict):
                        if doc_type == "UNKNOWN":
                            doc_type = data.get("document_type", "UNKNOWN")
                        
                        items = data.get("data", [])
                        if isinstance(items, list):
                            all_items.extend(items)
                    elif isinstance(data, list):
                         all_items.extend(data)

    except Exception as e:
        print(f"Error pdf {filepath.name}: {e}")

    if all_items:
        save_json({
            "broker": "bgsaxo",
            "source_file": filepath.name,
            "document_type": doc_type,
            "data": all_items
        }, OUTPUT_DIR, f"{filepath.name}.json")
