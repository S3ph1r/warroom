"""
ISIN-Based Reconciliation

Match transactions to holdings by ISIN for accurate comparison.
"""
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

# Load transactions
df = pd.read_csv("data/extracted/BG_SAXO_Transactions_Final.csv")
print(f"📊 Transactions: {len(df)}")

# Load holdings
with open("data/extracted/BG_SAXO_Holdings_Python.json", 'r') as f:
    holdings = json.load(f)['data']
print(f"📊 Holdings: {len(holdings)}")

# Build holdings by ISIN
holdings_by_isin = {}
for h in holdings:
    if h.get('isin'):
        holdings_by_isin[h['isin']] = {
            'ticker': h['ticker'],
            'name': h['name'],
            'quantity': h['quantity'],
            'asset_type': h.get('asset_type', '?')
        }

print(f"📊 Holdings with ISIN: {len(holdings_by_isin)}")

# Calculate net quantity per ISIN from transactions
txn_net = defaultdict(lambda: {'buy': 0, 'sell': 0, 'dist': 0, 'name': ''})

for _, row in df.iterrows():
    isin = row.get('isin')
    if pd.isna(isin) or not isin:
        continue
    
    qty = row['quantity'] if not pd.isna(row['quantity']) else 0
    op = row['operation']
    
    txn_net[isin]['name'] = row['name'][:40]
    
    if op == 'BUY':
        txn_net[isin]['buy'] += qty
    elif op == 'SELL':
        txn_net[isin]['sell'] += qty
    elif op == 'DISTRIBUTION':
        txn_net[isin]['dist'] += qty

print(f"📊 Unique ISINs in transactions: {len(txn_net)}")

# Compare
print("\n" + "=" * 100)
print("ISIN-BASED RECONCILIATION")
print("=" * 100)
print(f"{'ISIN':<14} {'Ticker':<14} {'Type':<6} {'H.Qty':>8} {'T.Buy':>8} {'T.Sell':>8} {'T.Dist':>8} {'T.Net':>8} {'Diff':>8} Status")
print("-" * 100)

matches = 0
mismatches = 0
not_found = 0
found_in_txn = 0

for isin, h in sorted(holdings_by_isin.items()):
    h_qty = h['quantity']
    
    if isin in txn_net:
        t = txn_net[isin]
        t_net = t['buy'] - t['sell'] + t['dist']
        diff = abs(h_qty - t_net)
        
        if diff < 0.01:
            status = "✅"
            matches += 1
        else:
            status = "❌"
            mismatches += 1
        
        print(f"{isin:<14} {h['ticker']:<14} {h['asset_type']:<6} {h_qty:>8.0f} {t['buy']:>8.0f} {t['sell']:>8.0f} {t['dist']:>8.0f} {t_net:>8.0f} {diff:>8.0f} {status}")
        found_in_txn += 1
    else:
        not_found += 1
        print(f"{isin:<14} {h['ticker']:<14} {h['asset_type']:<6} {h_qty:>8.0f} {'--':>8} {'--':>8} {'--':>8} {'--':>8} {h_qty:>8.0f} ❓")

print("\n" + "=" * 100)
print("SUMMARY:")
print(f"  ✅ Perfect Matches:     {matches}")
print(f"  ❌ Qty Mismatches:      {mismatches}")
print(f"  ❓ Not in Transactions: {not_found} (possibly bought before report period)")
print(f"  📊 Total Holdings:      {len(holdings_by_isin)}")
print(f"  📊 Match Rate:          {100*matches/len(holdings_by_isin):.1f}%")
print("=" * 100)

# List the not_found ones
if not_found > 0:
    print("\n❓ Holdings NOT in Transactions:")
    for isin, h in holdings_by_isin.items():
        if isin not in txn_net:
            print(f"  {h['ticker']:<15} {h['name'][:35]:<35} Qty={h['quantity']}")
