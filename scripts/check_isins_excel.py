"""Check Excel for specific ISINs"""
import pandas as pd
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")

# Load files
tx = pd.read_excel(INBOX / "Transactions_19807401_2024-11-26_2026-01-03.xlsx", engine="calamine")
pos = pd.read_excel(INBOX / "Posizioni_03-gen-2026_08_09_47.xlsx", engine="calamine")

isins = ['FR0010221234', 'US50125G3074']

for isin in isins:
    print(f"\n{'='*60}")
    print(f"ISIN: {isin}")
    print('='*60)
    
    # Holdings
    h = pos[pos['ISIN'] == isin]
    if not h.empty:
        row = h.iloc[0]
        print(f"HOLDINGS: {row['Strumento']} | Ticker: {row['Ticker']} | Qty: {row['Quantità']}")
    
    # Transactions
    txs = tx[tx['Instrument ISIN'] == isin]
    print(f"\nTRANSACTIONS ({len(txs)} records):")
    for _, row in txs.iterrows():
        print(f"  {row['Data della negoziazione'].date()} | {row['Tipo']}")
