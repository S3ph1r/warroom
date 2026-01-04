"""Debug the 2 mismatched ISINs"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction
from decimal import Decimal

session = SessionLocal()

isins = ['FR0010221234', 'US50125G3074']

print("=== HOLDINGS ===")
for isin in isins:
    h = session.query(Holding).filter(Holding.isin == isin, Holding.broker == 'BGSAXO').first()
    if h:
        print(f"{isin}: {h.name} | Ticker: {h.ticker} | Snapshot Qty: {h.quantity}")

print("\n=== TRANSACTIONS DETAIL ===")
for isin in isins:
    print(f"\n--- {isin} ---")
    txs = session.query(Transaction).filter(
        Transaction.isin == isin, 
        Transaction.broker == 'BGSAXO'
    ).order_by(Transaction.timestamp).all()
    
    running = Decimal("0")
    for tx in txs:
        if tx.operation == 'BUY':
            running += tx.quantity
        elif tx.operation == 'SELL':
            running -= tx.quantity
        print(f"  {tx.timestamp.date()} | {tx.operation:15} | qty: {tx.quantity:>10} | running: {running}")
    
    print(f"  FINAL CALCULATED: {running}")
    
    # Get snapshot
    h = session.query(Holding).filter(Holding.isin == isin, Holding.broker == 'BGSAXO').first()
    if h:
        print(f"  SNAPSHOT QTY:     {h.quantity}")
        print(f"  DIFF:             {h.quantity - running}")

session.close()
