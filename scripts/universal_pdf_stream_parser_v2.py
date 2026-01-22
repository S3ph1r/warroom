import sys
import re
import json
import pypdf

def clean_text(pdf_path, quick_test=True):
    """
    Extracts text and removes Header/Footer noise.
    quick_test: If True, only processes first 4 pages and last 2 pages.
    """
    reader = pypdf.PdfReader(pdf_path)
    clean_lines = []
    
    total_pages = len(reader.pages)
    if quick_test and total_pages > 6:
        # Indices: 0,1,2,3 AND N-2, N-1
        pages_to_process = list(range(4)) + list(range(total_pages - 2, total_pages))
    else:
        pages_to_process = range(total_pages)
        
    print(f"   📑 Processing pages: {pages_to_process}")
    
    # Noise Regexes (Headers, Footers, Page Numbers)
    noise_patterns = [
        r"^--- PAGE \d+ START ---$",
        r"^--- PAGE \d+ END ---$",
        r"^Transazioni,EUR",
        r"^Periodo di rendicontazione",
        r"^BG SAXO SIM",
        r"^/ Email: supporto",
        r"^Pagina \d+ di \d+",
        r"^Roberto Guareschi",
        r"^Valuta:EUR",
        r"^Conto/i:",
        r"^Generata il:",
        r"^Tipo Nome prodotto Tipo",
        r"W\.Europe Standard Time"
    ]
    
    for i in pages_to_process:
        page = reader.pages[i]
        text = page.extract_text()
        if not text: continue
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            is_noise = False
            for p in noise_patterns:
                if re.search(p, line):
                    is_noise = True
                    break
            
            # Additional heuristic: Date ranges in header
            if re.match(r"^\d{2}-[a-z]{3}-\d{4} a \d{2}-[a-z]{3}-\d{4}", line):
                is_noise = True
                
            if not is_noise:
                clean_lines.append(line)
                
    return clean_lines

def parse_lines(lines):
    transactions = []
    
    # regexes
    # 1. Date (e.g., 18-dic-2025) - usually implies a section start
    date_pattern = re.compile(r"^(\d{1,2}-[a-z]{3}-\d{4})")
    
    # 2. Transaction Start (The "Anchor")
    # Captures: 1=Trigger, 2=Product Name (The Middle), 3=Operation (The End)
    # Note: "Trasferimentodi liquidità" sometimes has no middle part if it is strictly a deposit.
    # We use a permissive middle match.
    start_pattern = re.compile(
        r"^(Contrattazione|Operazione sul capitale|Trasferimentodi liquidità)\s+(.*?)\s+(Acquista|Vendi|Dividendo|Scarico|Carico|Deposito|Scadenza)",
        re.IGNORECASE
    )
    
    # Deposit Case (Special): "Trasferimentodi liquidità Deposito..."
    deposit_pattern = re.compile(r"^(Trasferimentodi liquidità)\s+(Deposito)", re.IGNORECASE)

    isin_pattern = re.compile(r"(?:ISIN|^ISIN)\s*([A-Z]{2}[A-Z0-9]{10})")
    
    current_date = "UNKNOWN"
    current_txn = {}
    expecting_isin = False # Flag for multi-line ISIN
    
    for line in lines:
        # A. Check Date
        d_match = date_pattern.match(line)
        if d_match:
            current_date = d_match.group(1)
        
        # B. Check New Transaction Start
        start_match = start_pattern.match(line)
        deposit_match = deposit_pattern.match(line)
        
        is_new_txn = False
        new_txn_data = {}
        
        if start_match:
            is_new_txn = True
            trigger = start_match.group(1)
            product = start_match.group(2).strip()
            operation = start_match.group(3)
            
            new_txn_data = {
                "date": current_date,
                "type": trigger,
                "product_name": product,
                "operation": operation,
                "raw_start": line,
                "isin": None
            }
            
        elif deposit_match:
            is_new_txn = True
            new_txn_data = {
                "date": current_date,
                "type": "Deposito",
                "product_name": "Cash Deposit",
                "operation": "Deposito",
                "raw_start": line,
                "isin": None
            }
            
        if is_new_txn:
            # SAVE PREVIOUS
            if current_txn:
                transactions.append(current_txn)
            
            # START NEW
            current_txn = new_txn_data
            expecting_isin = False # Reset flag
            continue
            
        # C. If inside a transaction, look for details
        if current_txn:
            # 1. Check if we are waiting for ISIN from previous line
            if expecting_isin:
                # Try to find ISIN on this line
                # It might be standalone "US..." or strict
                # We check strict 12-char pattern
                strict_isin = re.search(r"([A-Z]{2}[A-Z0-9]{10})", line)
                if strict_isin:
                    current_txn['isin'] = strict_isin.group(1)
                    expecting_isin = False # Found it
                else:
                    # If this line is NOT an ISIN, but maybe we shouldn't give up immediately?
                    # The text dump shows ISIN is immediately next.
                    # If we don't find it effectively, we turn off the flag to avoid false positives later
                    pass 
                    
            # 2. Check for "ISIN" Label on this line
            if "ISIN" in line:
                # Case A: "ISIN US..." (Same line)
                isin_match = isin_pattern.search(line)
                if isin_match:
                    current_txn['isin'] = isin_match.group(1)
                    expecting_isin = False
                else:
                    # Case B: "ISIN" (Standalone) -> Expect next line
                    # But verify it's not part of "DISINVESTIMENTO" or other words
                    # The regex clean line usually leaves "ISIN" or "ID ISIN"
                    if line.strip() in ["ISIN", "ID ISIN", "Codice ISIN"]:
                        expecting_isin = True

    # Flush last
    if current_txn:
        transactions.append(current_txn)
        
    return transactions

def main(pdf_path):
    print(f"📂 Reading: {pdf_path}")
    lines = clean_text(pdf_path)
    print(f"🧹 Clean Lines: {len(lines)}")
    
    txns = parse_lines(lines)
    print(f"✅ Extracted {len(txns)} transactions.")
    
    out_path = pdf_path + ".stream_parsed.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": txns}, f, indent=2)
    print(f"💾 Saved: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python universal_pdf_stream_parser_v2.py <pdf>")
        sys.exit(1)
    main(sys.argv[1])
