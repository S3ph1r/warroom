"""
RECONCILIATION ENGINE
=====================
Performs the final validation and adjustment after ALL documents have been ingested.

LOGIC:
1. Load Final Holdings Snapshot (from CSV extraction)
2. Load Full Transaction History (aggregated from all PDF extractions)
3. For each asset:
    Calculated_Qty = Sum(BUYs) - Sum(SELLs) + Sum(TRANSFERS)
    Diff = Final_Holding_Qty - Calculated_Qty
    If Diff != 0:
        Generate RECONCILIATION transaction (Type: INITIAL_BALANCE / ADJUSTMENT)
4. Output verified ledger ready for DB
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def load_holdings(holdings_path: str) -> dict:
    """Load holdings snapshot. Returns dict: {isin_or_name: quantity}"""
    if not Path(holdings_path).exists():
        return {}
    
    with open(holdings_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    holdings = {}
    for h in data.get('holdings', []):
        # Prefer ISIN as key, fallback to Name
        key = h.get('isin') if h.get('isin') and len(str(h.get('isin'))) > 5 else h.get('name')
        if key:
            try:
                qty = float(h.get('quantity', 0))
                holdings[key] = qty
            except:
                pass
    return holdings

def aggregate_transactions(transaction_files: list) -> dict:
    """
    Load transactions from multiple files and aggregate by asset.
    Returns: {isin_or_name: {'buys': qty, 'sells': qty, 'events': []}}
    """
    aggregated = defaultdict(lambda: {'buys': 0.0, 'sells': 0.0, 'net_qty': 0.0, 'events': []})
    
    for file_path in transaction_files:
        if not Path(file_path).exists():
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Assuming the transaction parser outputs a list of transactions
        # If the structure is different, adjust here. 
        # Based on previous steps, we might need to standardise the output format first.
        # For this engine, we expect a standard structure.
        
        transactions = data.get('transactions', []) # Standardize this key in parser!
        
        for txn in transactions:
            # Prefer ISIN, fallback to Asset Name
            key = txn.get('isin') if txn.get('isin') and len(str(txn.get('isin'))) > 5 else txn.get('asset')
            if not key:
                continue
                
            qty = float(txn.get('quantity', 0))
            type_ = txn.get('type', '').upper()
            
            # Update aggregates
            if type_ in ['BUY', 'ACQUISTO']:
                aggregated[key]['buys'] += abs(qty)
                aggregated[key]['net_qty'] += abs(qty)
            elif type_ in ['SELL', 'VENDITA']:
                aggregated[key]['sells'] += abs(qty)
                aggregated[key]['net_qty'] -= abs(qty)
            
            aggregated[key]['events'].append(txn)
            
    return aggregated

def run_reconciliation(holdings_file: str, transaction_files: list):
    print("="*70)
    print("RECONCILIATION ENGINE STARTED")
    print("="*70)
    
    # 1. Load Data
    print(f"Loading holdings from: {Path(holdings_file).name}")
    holdings_map = load_holdings(holdings_file)
    print(f"  Assets in Snapshot: {len(holdings_map)}")
    
    print(f"Loading transactions from {len(transaction_files)} files...")
    history_map = aggregate_transactions(transaction_files)
    print(f"  Assets with History: {len(history_map)}")
    print()
    
    reconciliation_report = []
    generated_transactions = []
    
    # 2. Compare Holdings vs History
    all_keys = set(holdings_map.keys()) | set(history_map.keys())
    
    print(f"{'ASSET (ISIN/Name)':<35} | {'HOLDING':>10} | {'HISTORY':>10} | {'DIFF':>10} | {'ACTION':<15}")
    print("-" * 90)
    
    for key in all_keys:
        final_qty = holdings_map.get(key, 0.0)
        hist_qty = history_map[key]['net_qty']
        diff = final_qty - hist_qty
        
        action = "OK"
        if abs(diff) > 0.001: # Float tolerance
            action = "ADJUST"
            
            # Verify if this is a known asset
            asset_name = key
            # Try to find a better name from history events
            if history_map[key]['events']:
                asset_name = history_map[key]['events'][0].get('asset', key)
                
            # Generate Adjustment Transaction
            adj_txn = {
                "type": "RECONCILIATION",
                "asset": asset_name,
                "isin": key if len(key) > 5 else None, # Heuristic
                "quantity": diff,
                "date": "2025-01-01", # Default to start of period
                "note": f"Auto-generated to match snapshot. History={hist_qty}, Snapshot={final_qty}"
            }
            generated_transactions.append(adj_txn)
            
        print(f"{str(key)[:35]:<35} | {final_qty:>10.2f} | {hist_qty:>10.2f} | {diff:>10.2f} | {action:<15}")
        
        reconciliation_report.append({
            "asset": key,
            "holding_qty": final_qty,
            "history_net": hist_qty,
            "diff": diff,
            "status": action
        })

    print("-" * 90)
    print()
    print(f"Reconciliation Complete.")
    print(f"  Matched: {len([r for r in reconciliation_report if r['status'] == 'OK'])}")
    print(f"  Adjustments Generated: {len(generated_transactions)}")
    
    # 3. BUILD CONSOLIDATED LEDGER (The Truth Source)
    ledger = []
    
    # Process history events
    for key, data in history_map.items():
        base_asset = data['events'][0].get('asset', key) if data['events'] else key
        
        # Add historical events
        for event in data['events']:
            ledger.append({
                "date": event.get('date', 'Unknown'),
                "type": event.get('type', 'UNKNOWN'),
                "asset": base_asset,
                "quantity": float(event.get('quantity', 0)),
                "amount": float(event.get('amount', 0)),
                "currency": event.get('currency', 'EUR'),
                "source": "TRANSACTION_HISTORY"
            })
            
    # Add reconciliation events
    for adj in generated_transactions:
        ledger.append({
            "date": adj['date'],
            "type": "RECONCILIATION",
            "asset": adj['asset'],
            "quantity": adj['quantity'],
            "amount": 0.0,
            "currency": "EUR",
            "source": "SYSTEM_ADJUSTMENT",
            "note": adj.get('note', '')
        })
        
    output = {
        "report": reconciliation_report,
        "adjustments": generated_transactions,
        "consolidated_ledger": ledger,
        "timestamp": datetime.now().isoformat()
    }
    
    with open("scripts/reconciliation_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    print("Saved results to scripts/reconciliation_result.json")
    print(f"Generated Consolidated Ledger with {len(ledger)} entries.")
    return output

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdings", help="Path to holdings JSON")
    parser.add_argument("--transactions", help="Path to aggregated transactions JSON")
    args = parser.parse_args()

    # Default to BG Saxo if no args
    h_file = args.holdings or "scripts/Posizioni_19-dic-2025_17_49_12_extracted.json"
    t_file = args.transactions or "scripts/bgsaxo_transactions_full.json"
    
    t_files = [t_file]
    
    if Path(h_file).exists() and Path(t_files[0]).exists():
        run_reconciliation(h_file, t_files)
    else:
        print(f"Files not found: {h_file} or {t_file}")
