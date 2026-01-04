"""Check Eutelsat transactions"""
import pandas as pd
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")
tx = pd.read_excel(INBOX / "Transactions_19807401_2024-11-26_2026-01-03.xlsx", engine="calamine")
pos = pd.read_excel(INBOX / "Posizioni_03-gen-2026_08_09_47.xlsx", engine="calamine")

isin = 'FR0010221234'

print(f"=== {isin} (Eutelsat) ===\n")

# Holdings
h = pos[pos['ISIN'] == isin]
if not h.empty:
    row = h.iloc[0]
    print(f"HOLDINGS: {row['Strumento']} | Qty: {row['Quantità']}")

# All transactions for this ISIN
txs = tx[tx['Instrument ISIN'] == isin].sort_values('Data della negoziazione')
print(f"\nTRANSACTIONS ({len(txs)} records):")
for _, row in txs.iterrows():
    print(f"  {row['Data della negoziazione'].date()} | {row['Tipo di operazione']:25} | {row['Tipo']}")
