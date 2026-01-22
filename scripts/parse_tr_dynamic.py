import re
import sys
import json
import pdfplumber
from pathlib import Path

# Add project root to path for utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.parsing import robust_parse_decimal

def load_rules(pdf_path):
    vision_file = pdf_path.with_suffix('.vision.rules.json')
    rule_file = pdf_path.with_suffix('.pdf.rules.json')
    
    selected = None
    if vision_file.exists():
        selected = vision_file
        print(f"   ✨ Using Vision-Enhanced rules: {selected.name}")
    elif rule_file.exists():
        selected = rule_file
        print(f"   ℹ️  Using Standard rules: {selected.name}")
    else:
        print(f"ERROR: No rules file found for: {pdf_path.name}")
        sys.exit(1)
        
    with open(selected, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_tr_pdf(pdf_path):
    rules = load_rules(pdf_path)
    strategy = rules.get('strategy', 'block_based')
    
    print(f"\n{'='*60}")
    print(f" 🚜 PHASE 3: EXTRACTION ENGINE (Deterministic)")
    print(f"{'='*60}")
    print(f"   📂 File: {pdf_path.name}")
    print(f"   ⚙️  Strategy: {strategy}")
    
    # ---------------------------------------------------------
    # STRATEGY: LINE STATEFUL (For "Statement" style docs with Date Headers)
    # ---------------------------------------------------------
    if strategy == "line_stateful":
        config = rules.get('strategy_config', {})
        extractors = rules.get('field_extractors', {})
        
        # COMPILE REGEXES FROM JSON
        try:
            # "date_header_regex": "^(\\d{1,2}\\s\\w{3})$"
            date_header_re = re.compile(config.get('date_header_regex', r'IMPOSSIBLE_MATCH'), re.IGNORECASE)
            
            # "line_start_regex": "^(\\d{1,2}\\s\\w{3})|^(Bonifico|Commercio)"
            line_start_re = re.compile(config.get('line_start_regex', r'^.*'), re.IGNORECASE)
            
            # Field Extractors
            ex_date = re.compile(extractors.get('date', {}).get('regex', r'.*'), re.IGNORECASE)
            
            # Type Regex (Relaxed to handle 'CommercioBuy' etc.)
            type_regex = extractors.get('type', {}).get('regex', r'.*')
            ex_type = re.compile(type_regex, re.IGNORECASE)
            
            ex_amount = re.compile(extractors.get('amount', {}).get('regex', r'(-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€'), re.IGNORECASE)
            
        except re.error as e:
            print(f"REGEX COMPILATION ERROR: {e}")
            sys.exit(1)

        transactions = []
        current_tx = None
        current_date_context = "UNKNOWN_DATE"

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True) or ""
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    line_clean = line.strip()
                    if not line_clean: continue
                    
                    # VIRTUAL SPLIT: If a line has multiple triggers, split it!
                    # Example: "Commercio... Interessi..." -> ["Commercio...", "Interessi..."]
                    # We use the ex_type to find markers.
                    virtual_lines = [line_clean]
                    markers = list(ex_type.finditer(line_clean))
                    if len(markers) > 1:
                        # Split by the start position of each marker (except the first if it's at start)
                        virtual_lines = []
                        last_pos = 0
                        for m in markers:
                            if m.start() > 0:
                                virtual_lines.append(line_clean[last_pos:m.start()].strip())
                                last_pos = m.start()
                        virtual_lines.append(line_clean[last_pos:].strip())
                        virtual_lines = [v for v in virtual_lines if v]

                    for v_line in virtual_lines:
                        # 1. CHECK DATE HEADER (Update context but don't skip line!)
                        added_header_date = False
                        if date_header_re.search(v_line):
                            m = ex_date.search(v_line)
                            if m: 
                                current_date_context = m.group(0).strip()
                                added_header_date = True
                            # We DON'T continue here anymore, because the same line might have a transaction!

                        # 2. CHECK NEW TRANSACTION START (Only start if a valid TYPE is found)
                        m_type = ex_type.search(v_line)
                        if m_type:
                            if current_tx: transactions.append(current_tx)
                            
                            tx_type = m_type.group(1) if len(m_type.groups()) > 0 else m_type.group(0)

                            # Priority: 1. Date on current line, 2. Global date context
                            tx_date = current_date_context
                            m_date = ex_date.search(v_line)
                            if m_date: tx_date = m_date.group(0).strip()
                                
                            current_tx = {
                                "date": tx_date,
                                "type": tx_type,
                                "description": v_line,
                                "raw_lines": [v_line]
                            }
                        
                        # 3. CONTINUATION
                        elif current_tx and not added_header_date:
                             # Only treat as continuation if it wasn't a standalone date header
                             current_tx["description"] += " " + v_line
                             current_tx["raw_lines"].append(v_line)

        # Append last
        if current_tx: transactions.append(current_tx)

        # POST-PROCESS AMOUNTS (Generic heuristics)
        final_data = []
        for tx in transactions:
            full_blob = " ".join(tx['raw_lines'])
            
            # Extract all amounts
            amounts = ex_amount.findall(full_blob)
            
            amount_val = 0.0
            if amounts:
                # TR usually has [Amount, Balance] or [Amount, Fees, Balance]
                # Heuristic: the first one is usually the transaction amount in statement style
                # UNLESS it's a huge block, then it's trickier.
                clean_amts = []
                for a in amounts:
                    # If a is a tuple (from groups), take the first one
                    val_str = a[0] if isinstance(a, tuple) else a
                    clean_amts.append(float(robust_parse_decimal(val_str)))
                
                if clean_amts:
                    # In Trade Republic, the transaction amount is often the first one.
                    # But if we have [X, Y] and Y = X + Balance_Prev, then X is amount.
                    amount_val = clean_amts[0]
            
            final_data.append({
                "date": tx['date'],
                "type": tx['type'],
                "description": tx['description'][:200],
                "amount": amount_val,
                "full_text": full_blob
            })
            
        # SAVE
        out_file = pdf_path.with_suffix('.extracted.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2)
        print(f"SUCCESS: Extracted {len(final_data)} transactions.")

    # ---------------------------------------------------------
    # STRATEGY: BLOCK BASED (Legacy / BG Saxo style)
    # ---------------------------------------------------------
    elif strategy == "block_based":
        print("Executing Block-Based Parsing (Not implemented for TR yet)")
        # ... logic from parse_bgsaxo_dynamic.py ...
    
    else:
        print(f"Unknown Strategy: {strategy}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_tr_dynamic.py <pdf_file>")
        sys.exit(1)
    parse_tr_pdf(Path(sys.argv[1]))
