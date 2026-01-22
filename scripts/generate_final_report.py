"""
FINAL REPORT GENERATOR
======================
Generates a summary report of the ingestion and reconciliation process.
Reads:
- Extracted Holdings JSON
- Extracted Transactions JSON
- Database state
"""
import json
import pandas as pd
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def generate_report():
    print("="*80)
    print("BG SAXO: FINAL INGESTION & RECONCILIATION REPORT")
    print("="*80)
    
    # 1. HOLDINGS ANALYSIS
    holdings_file = "scripts/Posizioni_19-dic-2025_17_49_12_extracted.json"
    holdings_data = load_json(holdings_file)
    holdings = holdings_data.get('holdings', [])
    
    total_assets = len(holdings)
    total_value_eur = sum(h.get('market_value', 0) for h in holdings)
    
    print("\n1. HOLDINGS EXTRACTED (Snapshot)")
    print("-" * 40)
    print(f"Total Assets Identified: {total_assets}")
    print(f"Total Market Value (EUR): {total_value_eur:.2f}")
    
    # Asset types breakdown
    types = {}
    for h in holdings:
        t = h.get('asset_type', 'Unknown')
        types[t] = types.get(t, 0) + 1
    for t, c in types.items():
        print(f"  - {t}: {c}")

    # 2. TRANSACTIONS ANALYSIS
    txns_file = "scripts/bgsaxo_transactions_full.json"
    txns_data = load_json(txns_file)
    txns = txns_data.get('transactions', [])
    
    print("\n2. TRANSACTIONS EXTRACTED (History)")
    print("-" * 40)
    print(f"Total Pages Processed: {txns_data.get('last_processed_page', 0)} / {txns_data.get('total_pages', 0)}")
    print(f"Total Transactions Found: {len(txns)}")
    
    # Count by type
    txn_types = {}
    for t in txns:
        tt = t.get('type', 'UNKNOWN')
        txn_types[tt] = txn_types.get(tt, 0) + 1
    for t, c in txn_types.items():
        print(f"  - {t}: {c}")

    # 3. RECONCILIATION PREVIEW
    print("\n3. RECONCILIATION (Preview)")
    print("-" * 40)
    
    # Simple check for a few assets
    # Sum buys/sells for top assets
    print(f"{'ASSET':<30} | {'HOLDING':>8} | {'NET HISTORY':>12} | {'STATUS':<10}")
    print("-" * 70)
    
    for h in holdings[:10]: # Check first 10 holdings
        name = h.get('name', '')
        qty = h.get('quantity', 0)
        
        # Calculate net history for this asset
        net_hist = 0
        asset_txns = 0
        for t in txns:
            # Fuzzy match name
            if t.get('asset') and (t.get('asset') in name or name in t.get('asset')):
                t_qty = t.get('quantity', 0)
                type_ = t.get('type', '')
                if type_ == 'BUY': net_hist += t_qty
                elif type_ == 'SELL': net_hist -= abs(t_qty)
                asset_txns += 1
        
        status = "OK" if abs(qty - net_hist) < 0.1 else "GAP"
        if asset_txns == 0: status = "NO HIST"
        
        print(f"{name[:30]:<30} | {qty:>8.1f} | {net_hist:>12.1f} | {status:<10}")

    print("-" * 70)
    if len(txns) == 0:
        print("Waiting for transaction extraction to complete...")

if __name__ == "__main__":
    generate_report()
