
import json
import re
import sys
import pdfplumber
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Add project root to path for utils
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.parsing import robust_parse_decimal

class BGSaxoDynamicParser:
    def __init__(self, pdf_path, rules_path=None):
        self.pdf_path = Path(pdf_path)
        self.rules_path = Path(rules_path) if rules_path else self.pdf_path.with_suffix('.pdf.rules.json')
        self.rules = self._load_rules()
        self.current_date = None
        self.transactions = []

    def _load_rules(self):
        if not self.rules_path.exists():
            # Try removing just .pdf extension if logic differs
            alt_path = Path(str(self.pdf_path).replace('.pdf', '') + '.rules.json')
            if alt_path.exists():
                self.rules_path = alt_path
            else:
                raise FileNotFoundError(f"Rules file not found at {self.rules_path} or {alt_path}")
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _compile_regex(self, pattern):
        return re.compile(pattern, re.IGNORECASE)

    def parse_number(self, value):
        """Use the centralized robust numeric parser."""
        return robust_parse_decimal(value)

    def parse(self):
        print(f"[INFO] Parsing {self.pdf_path.name} using rules from {self.rules_path.name}")
        
        # Compile master regexes
        date_re = self._compile_regex(self.rules['date_trigger_regex'])
        start_re = self._compile_regex(self.rules['transaction_start_regex'])
        
        # Compile field extractors with DOTALL to allow matching across newlines if needed
        extractors = {}
        for key, config in self.rules['field_extractors'].items():
            # Add (?s) to pattern or compile with re.DOTALL? 
            # Safest is to use re.DOTALL when compiling
            extractors[key] = re.compile(config['regex'], re.IGNORECASE | re.DOTALL)

        current_block = [] # List of lines for current transaction

        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue

                    # 1. Check Date (Triggers a close of previous block)
                    date_match = date_re.search(line)
                    if date_match:
                        if current_block:
                            self._process_block(current_block, extractors)
                            current_block = []
                        
                        raw_date = date_match.group(0)
                        self.current_date = self._parse_date(raw_date)
                        continue # Assume Date Header is separate line
                    
                    # 2. Check Transaction Start (Triggers a close of previous block AND starts new one)
                    start_match = start_re.search(line)
                    if start_match:
                        if current_block:
                            self._process_block(current_block, extractors)
                        current_block = [line]
                    else:
                        # 3. Continuation line
                        if current_block:
                            current_block.append(line)
        
        # Process final block
        if current_block:
            self._process_block(current_block, extractors)

        return self.transactions

    def _parse_date(self, date_str):
        # Format: 28-nov-2024
        # Need Italian month mapping
        months = {
            'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06',
            'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
        }
        parts = date_str.lower().split('-')
        if len(parts) == 3:
            day, month_txt, year = parts
            month_num = months.get(month_txt, '01')
            return f"{year}-{month_num}-{day}"
        return date_str

    def _process_block(self, lines, extractors):
        # Join lines with newline to preserve structure for regexes that use start/end anchors
        # But also consider that some regexes might expect continuous text.
        # Given "Concatenation" warnings, typically spaces are missing in PDF extraction, 
        # so adding a space/newline is safe.
        block_text = "\n".join(lines)
        
        tx = {
            'date': self.current_date,
            'raw_line': lines[0], # Keep first line as primary ref
            'full_text': block_text, # Store full block for debug
            'type': 'UNKNOWN',
            'product': 'UNKNOWN',
            'amount': 0,
            'isin': None
        }

        # Extract Type
        if 'type_classifier' in extractors:
            m = extractors['type_classifier'].search(block_text)
            if m:
                tx['type'] = m.group(1)
        
        # Fallback type if regex failed but we know it started with a trigger
        if tx['type'] == 'UNKNOWN':
             # Heuristic: the first word of the block is likely the trigger
             first_word = lines[0].split()[0]
             tx['type'] = first_word

        # Extract Product
        if 'product_name' in extractors:
            m = extractors['product_name'].search(block_text)
            if m:
                val = m.group(0).strip()
                if not val and m.groups():
                    val = next((g for g in m.groups() if g), "")
                tx['product'] = val.strip()

        # Extract ISIN
        if 'isin' in extractors:
            m = extractors['isin'].search(block_text)
            if m:
                tx['isin'] = m.group(0)
                
        # Heuristic for Amount: Search for the LAST number in the block
        # Because we have multiple numbers/lines, we need to be careful.
        # Usually 'Amount' is the last field.
        amount_re = re.compile(r'(-?[\d.]+,[\d]{2})')
        amounts = amount_re.findall(block_text)
        if amounts:
            tx['amount'] = self.parse_number(amounts[-1])

        self.transactions.append(tx)

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_bgsaxo_dynamic.py <pdf_file> [rules_file]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    rules_file = sys.argv[2] if len(sys.argv) > 2 else None

    parser = BGSaxoDynamicParser(pdf_file, rules_file)
    try:
        results = parser.parse()
    except Exception as e:
        print(f"[ERROR] Error during parsing: {e}")
        sys.exit(1)

    # Output
    out_file = Path(pdf_file).with_suffix('.extracted.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"[SUCCESS] Extracted {len(results)} transactions.")
    print(f"[INFO] Saved to {out_file}")
    
    # Stats
    types = {}
    for tx in results:
        t = tx.get('type', 'UNKNOWN')
        types[t] = types.get(t, 0) + 1
    
    print("\n[STATS] Summary by Type:")
    for t, count in types.items():
        print(f"  {t}: {count}")

if __name__ == "__main__":
    main()
