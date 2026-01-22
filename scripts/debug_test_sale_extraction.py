"""
Debug Extract Sales Only
Test the parser against a specific file known to contain a "Sale" transaction.
"""
import sys
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).parent.parent))

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20241207 Monthly account statement Baader Bank nAW1Ve.pdf"

def parse_german_date(date_str):
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None

def parse_amount(num_str):
    s = num_str.strip()
    if not s: return Decimal(0)
    try:
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            s = s.replace(',', '.')
        return Decimal(s)
    except:
        return Decimal(0)

def test_extract():
    pdf_path = INBOX / TARGET
    if not pdf_path.exists():
        print(f"File not found: {TARGET}")
        return
        
    print(f"Parsing: {pdf_path.name}")
    
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    lines = full_text.split('\n')
    
    print(f"Total Lines: {len(lines)}")
    
    # First, find where Tesla is mentioned
    print("\n🔍 Looking for TESLA in this file:")
    for i, line in enumerate(lines):
        if "Tesla" in line or "US88160R1014" in line:
            start = max(0, i-5)
            end = min(len(lines), i+5)
            print(f"   Found at line {i+1}:")
            for k in range(start, end):
                marker = ">>" if k == i else "  "
                print(f"   {marker} L{k+1}: {lines[k].strip()}")
            print("   ---")
    print()
    
    txs = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        op = "UNKNOWN"
        if line == "Purchase" or line == "Savings Plan":
            op = "BUY"
        elif line == "Sale":
            op = "SELL"
        elif line == "Coupons/Dividends" or line == "Dividends":
            op = "DIVIDEND"
        
        if op != "UNKNOWN":
            print(f"\n🔍 Found Op: '{line}' at line {i+1}")
            
            # Look backwards for Date
            tx_date = datetime.now()
            for k in range(1, 5):
                if i-k >= 0:
                    d = parse_german_date(lines[i-k])
                    if d: 
                        tx_date = d
                        break
            print(f"   Date: {tx_date.date()}")
            
            # Look forward for Amount
            amount = Decimal(0)
            if i+1 < len(lines):
                possible_amt = lines[i+1].strip()
                if re.match(r'^[\d\.,]+$', possible_amt):
                    amount = parse_amount(possible_amt)
            print(f"   Amount: {amount}")
            
            # Look forward for ISIN and Qty (max 8 lines, stop at next op)
            isin = None
            qty = Decimal(0)
            name = "Unknown"
            
            for k in range(1, 8):
                if i+k >= len(lines): break
                subline = lines[i+k].strip()
                
                # Stop at next operation
                if subline in ["Purchase", "Sale", "Savings Plan", "Dividends", "Coupons/Dividends"]:
                    break
                
                if subline.startswith("ISIN") and isin is None:
                    parts = subline.split()
                    if len(parts) >= 2:
                        isin = parts[1]
                        if i+k-1 > i:
                            name = lines[i+k-1].strip()
                            if name == "-":
                                if i+k-2 > i:
                                    name = lines[i+k-2].strip()
                                    
                if subline.startswith("STK"):
                    m = re.search(r'STK\s+([\d\.,]+)', subline)
                    if m:
                        qty = parse_amount(m.group(1))
                        if isin:
                            break
                        
            print(f"   ISIN: {isin}, Name: {name}, Qty: {qty}")
            print(f"   -> TX: {op} {qty} @ {tx_date.date()}")
            
            txs.append({
                'op': op,
                'date': tx_date,
                'isin': isin,
                'name': name,
                'qty': qty,
                'amount': amount
            })
            
        i += 1
        
    print(f"\n✅ Total Transactions Found: {len(txs)}")
    for tx in txs:
        print(f"   {tx['date'].date()} | {tx['op']} | {tx['name'][:20]} | Qty: {tx['qty']}")

if __name__ == "__main__":
    test_extract()
