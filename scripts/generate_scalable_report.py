"""
SCALABLE CAPITAL REPORT GENERATOR
=================================
Reads:
- scripts/scalable_holdings.json
- scripts/scalable_transactions_full.json
"""
import json
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def generate_report():
    print("="*60)
    print("SCALABLE CAPITAL: INGESTION STATUS")
    print("="*60)
    
    # 1. HOLDINGS
    h_data = load_json("scripts/scalable_holdings.json")
    holdings = h_data.get('holdings', [])
    print(f"\n1. HOLDINGS EXTRACTED: {len(holdings)}")
    for h in holdings[:5]:
        print(f"  - {h.get('name')} | Qty: {h.get('quantity')} | Val: {h.get('market_value')}")
        
    # 2. TRANSACTIONS
    t_data = load_json("scripts/scalable_transactions_full.json")
    txns = t_data.get('transactions', [])
    print(f"\n2. TRANSACTIONS EXTRACTED: {len(txns)}")
    
    types = {}
    for t in txns:
        tt = t.get('type', 'UNKNOWN')
        types[tt] = types.get(tt, 0) + 1
    
    print("  Breakdown by Type:")
    for t, c in types.items():
        print(f"  - {t}: {c}")
        
    if txns:
        print("\n  Sample Transactions:")
        for t in txns[:3]:
            print(f"  - {t.get('date')} | {t.get('type')} | {t.get('asset')} | {t.get('amount')}")

if __name__ == "__main__":
    generate_report()
