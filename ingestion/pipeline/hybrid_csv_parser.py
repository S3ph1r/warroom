"""
Hybrid CSV Parser for Financial Holdings
Step 1: Deterministic parsing with csv.Sniffer (like Excel)
Step 2: Row validation with Ollama LLM
"""
import csv
import json
import requests
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Ollama config
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
OLLAMA_URL = "http://localhost:11434/api/chat"


def parse_csv_deterministic(file_path: str) -> tuple[List[str], List[List[str]]]:
    """
    Step 1: Parse CSV using Python's csv.Sniffer (same logic as Excel).
    Returns: (headers, rows)
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        # Read sample for sniffing
        sample = f.read(8192)
        f.seek(0)
        
        # Detect dialect (delimiter, quoting, etc)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            logger.info(f"   Detected delimiter: '{dialect.delimiter}'")
        except csv.Error:
            # Fallback to comma
            dialect = csv.excel
            logger.warning("   Could not detect dialect, using comma")
        
        # Read all rows
        reader = csv.reader(f, dialect)
        all_rows = list(reader)
    
    if not all_rows:
        return [], []
    
    # Find header row (first row with multiple non-empty cells)
    header_idx = 0
    for i, row in enumerate(all_rows):
        non_empty = [c for c in row if c.strip()]
        if len(non_empty) >= 5:  # Reasonable number of columns for a header
            header_idx = i
            break
    
    headers = [h.strip() for h in all_rows[header_idx]]
    data_rows = all_rows[header_idx + 1:]
    
    logger.info(f"   Header at row {header_idx}: {headers[:5]}...")
    logger.info(f"   Data rows: {len(data_rows)}")
    
    return headers, data_rows


def classify_rows_with_ollama(headers: List[str], rows: List[List[str]], batch_size: int = 20) -> List[bool]:
    """
    Step 2: Use Ollama to classify which rows are valid holdings vs summary/junk.
    Returns: List of booleans (True = valid, False = invalid)
    """
    logger.info(f"   Classifying {len(rows)} rows with Ollama ({OLLAMA_MODEL})...")
    
    results = []
    
    # Process in batches to avoid token limits
    for batch_start in range(0, len(rows), batch_size):
        batch = rows[batch_start:batch_start + batch_size]
        
        # Format rows as table for LLM
        table_text = "| " + " | ".join(headers[:8]) + " |\n"  # Limit columns for readability
        table_text += "|-" * len(headers[:8]) + "|\n"
        
        for i, row in enumerate(batch):
            row_data = row[:8]  # Limit columns
            # Pad if needed
            while len(row_data) < len(headers[:8]):
                row_data.append("")
            table_text += f"| " + " | ".join(str(c)[:20] for c in row_data) + f" | ROW_{batch_start + i}\n"
        
        prompt = f"""Analizza questa tabella di dati finanziari e classifica ogni riga.

{table_text}

Per ogni riga, rispondi SOLO con il formato:
ROW_X: VALID  (se è un asset reale con nome, quantità, prezzo)
ROW_X: INVALID  (se è una riga di summary, totale, intestazione ripetuta, o vuota)

Rispondi SOLO con le classificazioni, una per riga:"""

        try:
            response = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }, timeout=120)
            
            if response.status_code == 200:
                content = response.json().get('message', {}).get('content', '')
                
                # Parse response
                batch_results = []
                for i in range(len(batch)):
                    row_id = f"ROW_{batch_start + i}"
                    if f"{row_id}: VALID" in content or f"{row_id}:VALID" in content:
                        batch_results.append(True)
                    else:
                        batch_results.append(False)
                
                results.extend(batch_results)
                valid_count = sum(batch_results)
                logger.info(f"   Batch {batch_start//batch_size + 1}: {valid_count}/{len(batch)} valid")
            else:
                logger.error(f"   Ollama error: {response.status_code}")
                # Fallback: assume all valid
                results.extend([True] * len(batch))
                
        except Exception as e:
            logger.error(f"   Ollama exception: {e}")
            results.extend([True] * len(batch))
    
    return results


def clean_number(val: str) -> float:
    """Convert European format number to float."""
    if not val or not val.strip():
        return 0.0
    s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip()
    try:
        return float(s)
    except:
        return 0.0


def rows_to_holdings(headers: List[str], rows: List[List[str]], valid_mask: List[bool]) -> List[Dict]:
    """
    Convert validated rows to holdings schema.
    """
    # Map Italian headers to schema
    header_lower = [h.lower() for h in headers]
    
    def find_col(keywords):
        for kw in keywords:
            for i, h in enumerate(header_lower):
                if kw in h:
                    return i
        return -1
    
    col_name = find_col(['strumento', 'descrizione', 'nome'])
    col_qty = find_col(['quantità', 'qty', 'quantity'])
    col_currency = find_col(['valuta', 'currency'])
    col_price = find_col(['prz. corrente', 'prezzo corrente', 'ultimo'])
    col_value = find_col(['valore', 'controvalore', 'esposizione'])
    col_isin = find_col(['isin'])
    
    logger.info(f"   Column mapping: name={col_name}, qty={col_qty}, currency={col_currency}")
    
    holdings = []
    for row, is_valid in zip(rows, valid_mask):
        if not is_valid:
            continue
        
        # Extract with safety
        def get_col(idx, default=''):
            if idx >= 0 and idx < len(row):
                return row[idx].strip()
            return default
        
        name = get_col(col_name)
        if not name:
            continue
        
        holding = {
            'ticker': name.split()[0][:10].upper() if name else 'UNKNOWN',  # First word as ticker approx
            'name': name,
            'isin': get_col(col_isin) if col_isin >= 0 else None,
            'quantity': clean_number(get_col(col_qty)),
            'currency': get_col(col_currency, 'EUR').upper()[:3],
            'current_price': clean_number(get_col(col_price)),
            'current_value': clean_number(get_col(col_value)),
            'asset_type': 'STOCK'  # Default
        }
        
        # ETF detection
        if 'ETF' in name.upper() or 'UCITS' in name.upper():
            holding['asset_type'] = 'ETF'
        
        holdings.append(holding)
    
    return holdings


def parse_holdings_hybrid(file_path: str) -> List[Dict]:
    """
    Main function: Hybrid CSV parsing for holdings.
    """
    logger.info(f"📄 Parsing: {Path(file_path).name}")
    
    # Step 1: Deterministic parsing
    logger.info("Step 1: Deterministic CSV parsing...")
    headers, rows = parse_csv_deterministic(file_path)
    
    if not headers or not rows:
        logger.error("   No data found!")
        return []
    
    # Step 2: LLM classification
    logger.info("Step 2: LLM row classification...")
    valid_mask = classify_rows_with_ollama(headers, rows)
    
    valid_count = sum(valid_mask)
    logger.info(f"   Valid rows: {valid_count}/{len(rows)}")
    
    # Step 3: Convert to schema
    logger.info("Step 3: Converting to holdings schema...")
    holdings = rows_to_holdings(headers, rows, valid_mask)
    
    logger.info(f"✅ Extracted {len(holdings)} holdings")
    
    return holdings


# Test
if __name__ == "__main__":
    csv_file = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv"
    
    holdings = parse_holdings_hybrid(csv_file)
    
    print("\n" + "="*60)
    print("SAMPLE RESULTS (first 3 records)")
    print("="*60)
    for i, h in enumerate(holdings[:3]):
        print(f"\nRecord {i+1}:")
        for k, v in h.items():
            print(f"  {k}: {v}")
