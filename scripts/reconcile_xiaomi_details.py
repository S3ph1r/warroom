import re
from pathlib import Path

def parse_xiaomi_history():
    history_file = Path("xiaomi_detailed_history.txt")
    if not history_file.exists():
        print("History file not found.")
        return

    try:
        content = history_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = history_file.read_text(encoding='utf-16le')
    blocks = content.split("=" * 60)
    
    movements = []
    
    for block in blocks:
        if not block.strip(): continue
        
        file_match = re.search(r'FILE: (.*)', block)
        filename = file_match.group(1) if file_match else "Unknown"
        
        # Look for dates
        dates = re.findall(r'(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})', block)
        date = dates[0] if dates else "Unknown Date"
        
        # Look for quantities (STK or pz.)
        stk_matches = re.findall(r'STK\s+([\d\.,]+)', block)
        pz_matches = re.findall(r'([\d\.,]+)\s+pz\.', block)
        
        # Look for operations
        op = "INFO"
        if "Purchase" in block or "Acquisto" in block or "Savings Plan" in block:
            op = "BUY"
        elif "Sale" in block or "Vendita" in block:
            op = "SELL"
        elif "Dividendo" in block or "Dividend" in block or "Distribuzione" in block:
            op = "DIVIDEND"
            
        qty = Decimal(0)
        if stk_matches:
            qty = stk_matches[0]
        elif pz_matches:
            qty = pz_matches[0]
            
        if qty != Decimal(0) or op != "INFO":
            movements.append({
                "date": date,
                "file": filename,
                "op": op,
                "qty": qty
            })

    # Sort and print
    print(f"{'Date':<12} | {'Op':<8} | {'Qty':<10} | {'File'}")
    print("-" * 80)
    for m in sorted(movements, key=lambda x: x['date']):
        print(f"{m['date']:<12} | {m['op']:<8} | {m['qty']:<10} | {m['file']}")

if __name__ == "__main__":
    from decimal import Decimal
    parse_xiaomi_history()
