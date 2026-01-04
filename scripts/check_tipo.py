"""Check transaction Tipo field format"""
import pandas as pd
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")
tx = pd.read_excel(INBOX / "Transactions_19807401_2024-11-26_2026-01-03.xlsx", engine="calamine")

print("COLUMNS:", list(tx.columns))
print()
print("SAMPLE Contrattazione rows (Tipo field):")
trades = tx[tx['Tipo di operazione'] == 'Contrattazione'].head(10)
for i, (_, row) in enumerate(trades.iterrows()):
    tipo = row['Tipo']
    strumento = row['Strumento']
    print(f"  {i+1}. Tipo: '{tipo}'")
    print(f"     Strumento: {strumento}")
    print()
