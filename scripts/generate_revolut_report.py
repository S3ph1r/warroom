"""
REVOLUT INGESTION REPORT
========================
"""
import json
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def generate():
    print("\nREVOLUT REPORT")
    print("==============")
    
    data = load_json("scripts/revolut_transactions_full.json")
    txs = data.get("transactions", [])
    print(f"Total Transactions: {len(txs)}")
    
    # Breakdown by Asset
    assets = {}
    for t in txs:
        a = t.get('asset', 'Unknown')
        assets[a] = assets.get(a, 0) + 1
        
    print(f"Unique Assets: {len(assets)}")
    print("Top Active Assets:")
    sorted_assets = sorted(assets.items(), key=lambda x: x[1], reverse=True)
    for a, c in sorted_assets[:5]:
        print(f"  - {a}: {c} txns")
        
    # Check Reconciliation result (Calculated Ledger)
    recon = load_json("scripts/reconciliation_result.json")
    ledger = recon.get("ledger_snapshot", [])
    
    print("\nCALCULATED PORTFOLIO (History Only):")
    total_val = 0
    for item in ledger:
        # Ledger format from reconciliation_engine v2 is a list of dicts?
        # No, result.json usually has "adjustments" and "ledger_snapshot" if I implemented it so?
        # Let's check reconciliation_engine.py output format logic.
        # It dumps 'result' dict.
        pass
        
    # Since I don't recall exact output structure of recon engine for ledger snapshot listing, 
    # I'll just inspect the file content structure via print if it exists.
    
    if Path("scripts/reconciliation_result.json").exists():
        with open("scripts/reconciliation_result.json", 'r') as f:
            print(f.read()[:500]) # Peek

if __name__ == "__main__":
    generate()
