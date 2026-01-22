"""
Pre-Load Reconciliation Check

Compare extracted transactions (CSV) with Holdings (JSON)
to verify data quality BEFORE loading to database.

If PDF has complete history: SUM(BUY) - SUM(SELL) = Holdings Qty
"""
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

# Load extracted transactions
txn_path = Path("data/extracted/BG_SAXO_Transactions_Parsed.csv")
df_txn = pd.read_csv(txn_path)
print(f"📊 Loaded {len(df_txn)} transactions from CSV")

# Load holdings
holdings_path = Path("data/extracted/BG_SAXO_Holdings_Python.json")
with open(holdings_path, 'r', encoding='utf-8') as f:
    holdings = json.load(f)['data']  # Key is 'data', not 'holdings'
print(f"📊 Loaded {len(holdings)} holdings")

# Calculate net quantity per asset name from transactions
# Since we don't have tickers in transactions, we match by NAME
txn_net = defaultdict(float)
for _, row in df_txn.iterrows():
    name = row['name']
    qty = row['quantity']
    op = row['operation']
    
    if op == 'BUY':
        txn_net[name] += qty
    elif op == 'SELL':
        txn_net[name] -= qty

print(f"\n📊 Unique assets in transactions: {len(txn_net)}")

# Holdings by name (for matching since we don't have tickers in txn)
holdings_by_name = {}
for h in holdings:
    # Use partial name matching
    name_key = h['name'][:30].lower().replace(' ', '').replace('.', '').replace(',', '')
    holdings_by_name[name_key] = {
        'ticker': h['ticker'],
        'name': h['name'],
        'quantity': h['quantity']
    }

print(f"📊 Holdings names indexed: {len(holdings_by_name)}")

# Match and compare
print("\n" + "=" * 80)
print("RECONCILIATION RESULTS")
print("=" * 80)

matches = 0
mismatches = 0
not_found = 0

results = []
for txn_name, txn_qty in sorted(txn_net.items()):
    # Clean name for matching
    name_key = txn_name[:30].lower().replace(' ', '').replace('.', '').replace(',', '')
    
    holding = holdings_by_name.get(name_key)
    
    if holding:
        h_qty = holding['quantity']
        diff = abs(txn_qty - h_qty)
        status = "✅" if diff < 0.01 else "❌"
        
        if diff < 0.01:
            matches += 1
        else:
            mismatches += 1
        
        results.append({
            'name': txn_name[:30],
            'ticker': holding['ticker'],
            'txn_net': txn_qty,
            'holding': h_qty,
            'diff': diff,
            'status': status
        })
    else:
        # Check if it's a sold position (net = 0 or negative)
        if txn_qty <= 0:
            not_found += 1  # Completely sold, expected not in holdings
        else:
            results.append({
                'name': txn_name[:30],
                'ticker': 'NOT FOUND',
                'txn_net': txn_qty,
                'holding': 0,
                'diff': txn_qty,
                'status': '❓'
            })

# Print results
print(f"\n{'Name':<35} {'Ticker':<15} {'Txn Net':>10} {'Holding':>10} {'Diff':>10} Status")
print("-" * 90)

for r in results[:30]:  # First 30
    print(f"{r['name']:<35} {r['ticker']:<15} {r['txn_net']:>10.2f} {r['holding']:>10.2f} {r['diff']:>10.2f} {r['status']}")

if len(results) > 30:
    print(f"... and {len(results) - 30} more")

print("\n" + "=" * 80)
print(f"SUMMARY:")
print(f"  ✅ Matches (qty matches): {matches}")
print(f"  ❌ Mismatches (different qty): {mismatches}")
print(f"  ❓ Not in holdings: {len([r for r in results if r['ticker'] == 'NOT FOUND'])}")
print(f"  📤 Sold positions (not in holdings): {not_found}")
print("=" * 80)
