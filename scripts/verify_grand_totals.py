"""
VERIFY GRAND TOTALS & QUANTITIES
================================
Validates extraction by comparing Snapshot (Truth) vs History (derived).
Handles currency conversion for Grand Total estimation.
"""
import json
import pandas as pd
from pathlib import Path

# Approximate rates for verification (EUR base)
FX_RATES = {
    "EUR": 1.0,
    "USD": 0.95,  # Dec 2025 estimate
    "CAD": 0.68,
    "HKD": 0.12,
    "DKK": 0.134,
    "GBP": 1.18
}

def get_rate(currency):
    return FX_RATES.get(currency.strip().upper(), 1.0)

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_broker(name, holdings_file, transactions_file):
    print(f"\n{'='*30}")
    print(f"VERIFICATION: {name}")
    print(f"{'='*30}")
    
    if not Path(holdings_file).exists() or not Path(transactions_file).exists():
        print("Files not found.")
        return

    # 1. LOAD DATA
    h_data = load_json(holdings_file)
    t_data = load_json(transactions_file)
    
    holdings = h_data.get('holdings', [])
    transactions = t_data.get('transactions', [])
    
    print(f"Holdings Loaded: {len(holdings)}")
    print(f"Transactions Loaded: {len(transactions)}")
    
    # 2. CALCULATE HOLDINGS TOTALS
    total_h_value_eur = 0.0
    h_qty_map = {}
    
    print("\n--- SNAPSHOT (Holdings) ---")
    for h in holdings:
        qty = float(h.get('quantity', 0))
        val = float(h.get('market_value', 0) if h.get('market_value') else 0)
        # Use purchase price as fallback if MV is missing (common in some extracts)
        if val == 0 and h.get('purchase_price'):
             val = qty * float(h.get('purchase_price'))
             
        ccy = h.get('currency', 'EUR')
        rate = get_rate(ccy)
        val_eur = val * rate
        
        total_h_value_eur += val_eur
        
        # Key: Try ISIN first, then simplify Name
        key = h.get('isin', '')
        if not key:
            key = h.get('name', '').split(' ')[0].upper() # Simple fuzzy key
        h_qty_map[key] = {'qty': qty, 'val_eur': val_eur, 'name': h.get('name')}

    print(f"Total Snapshot Value: € {total_h_value_eur:,.2f}")
    
    # 3. CALCULATE TRANSACTION TOTALS
    t_qty_map = {}
    total_t_invested = 0.0
    
    for t in transactions:
        t_type = t.get('type', '').upper()
        if t_type not in ['BUY', 'SELL']:
            continue
            
        qty = float(t.get('quantity', 0))
        amt = float(t.get('amount', 0))
        ccy = t.get('currency', 'EUR')
        rate = get_rate(ccy)
        
        # Invested capital (cash flow)
        total_t_invested += (amt * rate)  # Negative for buy, Positive for Sell
        
        # Quantity
        # Strategy: Use ISIN or Name matching same as above
        t_isin = t.get('isin', '')
        t_asset = t.get('asset', '')
        
        # Try to match to H keys
        matched_key = None
        
        # 1. Direct ISIN match
        if t_isin in h_qty_map:
            matched_key = t_isin
        # 2. Name fuzzy
        elif t_asset.split(' ')[0].upper() in h_qty_map:
             matched_key = t_asset.split(' ')[0].upper()
        # 3. Create new if no match (sold positions?)
        else:
             matched_key = t_isin if t_isin else t_asset.split(' ')[0].upper()
        
        if matched_key not in t_qty_map:
            t_qty_map[matched_key] = 0.0
            
        # For BUY, quantity is usually negative in Saxo PDF? No, let's check.
        # Check snippet: BUY Qty -2. So abs() needed?
        # Saxo PDF: "Quantity -2", "Amount 603". This implies flow.
        # Usually: Buy = +Qty, -Cash.
        # But Saxo PDF Extract snippet showed: "type": "BUY", "quantity": -2.
        # Wait, let's re-read the JSON snippet carefully.
        # Snippet: "type": "BUY", "asset": "Alphabet", "quantity": -2.
        # This implies the extraction logic extracted the sign as present in PDF.
        # If Saxo represents Buys as negative flow of cash AND negative quantity? That would be weird.
        # Let's assume standard logic: 
        # If Type is BUY, we ADD to holdings.
        # If Type is SELL, we SUBTRACT.
        # We will take abs(quantity) and apply sign based on Type.
        
        abs_q = abs(qty)
        if t_type == 'BUY':
            t_qty_map[matched_key] += abs_q
        elif t_type == 'SELL':
            t_qty_map[matched_key] -= abs_q

    print("\n--- QUANTITIES CHECK (Top Mismatches) ---")
    print(f"{'ASSET':<30} | {'HOLDING':<10} | {'HISTORY':<10} | {'DELTA':<10}")
    print("-" * 70)
    
    matches = 0
    mismatches = 0
    
    # Check all Holdings against History
    for key, h_data in h_qty_map.items():
        h_q = h_data['qty']
        t_q = t_qty_map.get(key, 0.0)
        delta = h_q - t_q
        
        if abs(delta) < 0.01:
            matches += 1
        else:
            mismatches += 1
            name = h_data['name'][:28]
            print(f"{name:<30} | {h_q:<10.2f} | {t_q:<10.2f} | {delta:<10.2f}")
            
    print("-" * 70)
    print(f"Grand Total Match Rate: {matches}/{matches+mismatches} Assets")
    
if __name__ == "__main__":
    # BG SAXO
    verify_broker("BG SAXO", 
                  "scripts/Posizioni_19-dic-2025_17_49_12_extracted.json",
                  "scripts/bgsaxo_transactions_full.json")
                  
    # SCALABLE
    verify_broker("SCALABLE CAPITAL", 
                  "scripts/scalable_holdings.json",
                  "scripts/scalable_transactions_full.json")
