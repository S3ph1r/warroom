
import json
import re
from pathlib import Path

INPUT_FILE = "scripts/tr_transactions.json"
OUTPUT_FILE = "scripts/tr_final.json"

def clean_isin(val):
    if not val: return ""
    # Remove quotes, commas
    clean = re.sub(r'[^A-Z0-9]', '', val)
    # ISIN is 12 chars
    if len(clean) > 12:
        return clean[:12]
    return clean

def sanitize():
    print("SANITIZING TRade Republic Data...")
    if not Path(INPUT_FILE).exists():
        print("Input not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    txns = data.get("transactions", [])
    valid_txns = []
    
    for t in txns:
        # 1. Clean ISIN
        raw_isin = t.get("isin", "")
        t["isin"] = clean_isin(raw_isin)
        
        # 2. Fix Quantity
        try:
            qty = float(t.get("quantity", 0))
        except:
            qty = 0.0
            
        try:
            amt = float(t.get("amount", 0))
        except:
            amt = 0.0
            
        ttype = t.get("type", "UNKNOWN").upper()
        
        # Rule: BUY with Negative Qty -> Flip it (Mistral error)
        # Check Amount: If Amount is negative (Cost), it's a Buy.
        if ttype == "BUY":
            if amt < 0 and qty < 0:
                qty = abs(qty)
            elif amt > 0 and qty > 0:
                 # Positive Amount on BUY? Refund? Or Sell mislabeled?
                 pass
        
        t["quantity"] = qty
        t["amount"] = amt
        
        # 3. Clean Asset Name
        name = t.get("asset", "").strip()
        # Remove leading comma if present
        if name.startswith(","):
            name = name.lstrip(", ")
        # Fix known broken names
        if "ACLE CORP." in name:
            name = "ORACLE CORP"
        if "RL ZEISS" in name:
            name = "CARL ZEISS MEDITEC"
        if "ML HOLDING" in name:
            name = "ASML HOLDING" # Assumption
        if "G9830T1067" in name: # Xiaomi ISIN fragment
            name = "XIAOMI CORP"
            if not t["isin"]: t["isin"] = "KYG9830T1067"

        t["asset"] = name
        
        valid_txns.append(t)
        
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"transactions": valid_txns}, f, indent=2)
        
    print(f"Sanitized {len(valid_txns)} transactions. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    sanitize()
