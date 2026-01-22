
import re
import json
import sys
import pdfplumber
from pathlib import Path
from datetime import datetime

def load_rules(rules_path):
    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_and_stitch_text(pdf_path, noise_patterns):
    """
    Extracts text from all pages and removes lines matching noise patterns.
    Returns a list of clean lines.
    """
    print(f"🧵 Stitching PDF: {pdf_path}")
    full_text_lines = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"   Pages: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                is_noise = False
                for pattern in noise_patterns:
                    if re.search(pattern, line):
                        is_noise = True
                        break
                
                if not is_noise:
                    # Strip whitespace but keep the line structure
                    clean_line = line.strip()
                    if clean_line:
                        full_text_lines.append(clean_line)
                        
    return full_text_lines

def parse_with_state_machine(lines, rules):
    """
    Iterates lines and maintains state (Current Date, Current Transaction).
    """
    date_trigger = re.compile(rules['date_trigger_regex'], re.IGNORECASE)
    txn_trigger = re.compile(rules['transaction_start_regex'], re.IGNORECASE)
    
    field_extractors = {}
    for key, config in rules['field_extractors'].items():
        field_extractors[key] = re.compile(config['regex'], re.IGNORECASE)

    transactions = []
    
    current_date = None
    current_block = [] # List of lines for current transaction
    
    # Helper to flush current block
    def flush_block():
        if not current_block:
            return
            
        # Join block into single string for regex search
        block_text = " ".join(current_block)
        
        record = {
            "date": current_date,
            "raw_block": block_text[:100] + "..." # Snippet for debug
        }
        
        # Apply Field Extractors
        for field, pattern in field_extractors.items():
            match = pattern.search(block_text)
            if match:
                # If named group 'value' exists, use it, else use full match or specific groups
                if 'value' in match.groupdict():
                    record[field] = match.group('value').strip()
                elif 'qty' in match.groupdict() and 'price' in match.groupdict():
                    record['quantity'] = match.group('qty')
                    record['price'] = match.group('price')
                elif 'qty' in match.groupdict():
                     record['quantity'] = match.group('qty')
                elif 'price' in match.groupdict():
                     record['price'] = match.group('price')
                else:
                    record[field] = match.group(0).strip()
        
        # Post-Processing: Ticker Logic
        # Often the "product" field contains the ticker or name. 
        if 'product' in record:
            # Cleanup common noise in product name/ticker
            # This is specific to the observed rules but we keep it generic enough
            pass

        transactions.append(record)
    
    # --- MAIN LOOP ---
    for line in lines:
        # 1. Check Date Trigger
        date_match = date_trigger.match(line)
        if date_match:
            # New Date found. 
            # Note: A date line might NOT close the previous transaction if the transaction spans pages?
            # Actually, in this PDF, date headers are distinct.
            # But we don't close the current block just because we found a date, 
            # UNLESS the date line is implicitly a separator.
            # Let's assume Date Header resets state for subsequent transactions.
            current_date = line.strip()
            continue
            
        # 2. Check Transaction Start
        if txn_trigger.match(line):
            # Previous block ends here. Flush it.
            flush_block()
            
            # Start new block
            current_block = [line]
            
        else:
            # 3. Accumulate lines into current block
            if current_block:
                current_block.append(line)
                
    # Flush last block
    flush_block()
    
    return transactions

def main(pdf_path, rules_path):
    rules = load_rules(rules_path)
    
    # 1. Clean & Stitch
    clean_lines = clean_and_stitch_text(pdf_path, rules['noise_patterns'])
    
    print(f"   Clean Lines: {len(clean_lines)}")
    # Debug: dump first 20 clean lines
    # print("\n".join(clean_lines[:20]))
    
    # 2. Parse
    transactions = parse_with_state_machine(clean_lines, rules)
    
    print(f"✅ Extracted {len(transactions)} transactions.")
    
    # 3. Save
    out_path = pdf_path + ".stream_parsed.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": transactions}, f, indent=2)
        
    print(f"   Saved to: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python universal_pdf_stream_parser.py <pdf_path> <rules_path>")
        sys.exit(1)
        
    main(sys.argv[1], sys.argv[2])
