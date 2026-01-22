"""
Deep Investigation of Mismatches

1. Search PDF for Eutelsat and KULR transactions
2. List all unmatched holdings
3. Verify holdings breakdown (48 stock, 7 ETF)
4. Calculate net cash position
"""
import pdfplumber
import pandas as pd
import json
from pathlib import Path
import re

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

print("=" * 80)
print("DEEP INVESTIGATION")
print("=" * 80)

# 1. Search PDF for Eutelsat and KULR
print("\n📋 1. SEARCHING PDF FOR EUTELSAT & KULR")
print("-" * 50)

with pdfplumber.open(pdf_path) as pdf:
    for keyword in ['Eutelsat', 'KULR']:
        print(f"\n🔍 Searching for '{keyword}':")
        found = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if keyword.lower() in text.lower():
                # Extract the relevant lines
                for line in text.split('\n'):
                    if keyword.lower() in line.lower():
                        found.append(f"  Page {i+1}: {line[:100]}")
        print(f"  Found in {len(found)} lines:")
        for f in found[:20]:
            print(f)
        if len(found) > 20:
            print(f"  ... and {len(found)-20} more")

# 2. Load holdings and transactions
print("\n\n📋 2. UNMATCHED HOLDINGS ANALYSIS")
print("-" * 50)

# Load holdings
with open("data/extracted/BG_SAXO_Holdings_Python.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
    holdings = data['data']

# Count by type
stocks = [h for h in holdings if h.get('asset_type') == 'STOCK']
etfs = [h for h in holdings if h.get('asset_type') == 'ETF']
print(f"Holdings breakdown: {len(stocks)} STOCK + {len(etfs)} ETF = {len(holdings)} total")

# Load transactions
df_txn = pd.read_csv("data/extracted/BG_SAXO_Transactions_Parsed.csv")

# Calculate net per asset
txn_net = {}
for _, row in df_txn.iterrows():
    name = row['name'][:30].lower().replace(' ', '').replace('.', '')
    qty = row['quantity']
    op = row['operation']
    
    if name not in txn_net:
        txn_net[name] = 0
    
    if op == 'BUY':
        txn_net[name] += qty
    elif op == 'SELL':
        txn_net[name] -= qty

# Check each holding
print("\n📊 Holdings NOT matching with transactions:")
print(f"{'Name':<35} {'Ticker':<15} {'Type':<6} {'Holding':>8} {'Txn Net':>8} {'Diff':>8}")
print("-" * 90)

unmatched = []
for h in holdings:
    name_key = h['name'][:30].lower().replace(' ', '').replace('.', '').replace(',', '')
    h_qty = h['quantity']
    t_qty = txn_net.get(name_key, 0)
    diff = abs(h_qty - t_qty)
    
    if diff > 0.01:
        unmatched.append({
            'name': h['name'][:35],
            'ticker': h['ticker'],
            'type': h.get('asset_type', '?'),
            'holding': h_qty,
            'txn_net': t_qty,
            'diff': diff
        })
        print(f"{h['name'][:35]:<35} {h['ticker']:<15} {h.get('asset_type','?'):<6} {h_qty:>8.0f} {t_qty:>8.0f} {diff:>8.0f}")

print(f"\nTotal unmatched: {len(unmatched)}/{len(holdings)}")

# 3. Cash calculation
print("\n\n📋 3. CASH POSITION CALCULATION")
print("-" * 50)

deposits = df_txn[df_txn['operation'] == 'DEPOSIT']['price'].sum()
withdrawals = df_txn[df_txn['operation'] == 'WITHDRAW']['price'].sum()
net_cash_in = deposits - withdrawals

print(f"Total Deposits:    €{deposits:,.2f}")
print(f"Total Withdrawals: €{withdrawals:,.2f}")
print(f"Net Cash In:       €{net_cash_in:,.2f}")

# Also calculate total spent on BUY
buys = df_txn[df_txn['operation'] == 'BUY']
buy_total = 0
for _, row in buys.iterrows():
    buy_total += row['quantity'] * row['price']

print(f"\nTotal Invested (BUY):  €{buy_total:,.2f}")

sells = df_txn[df_txn['operation'] == 'SELL']
sell_total = 0
for _, row in sells.iterrows():
    sell_total += row['quantity'] * row['price']
    
print(f"Total from Sales (SELL): €{sell_total:,.2f}")

print(f"\nExpected Cash Balance: €{net_cash_in - buy_total + sell_total:,.2f}")
