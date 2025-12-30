
import sys
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction

session = SessionLocal()

print("--- OPERATION TYPES IN DB ---")
from sqlalchemy import func
ops = session.query(Transaction.operation, func.count(Transaction.id))\
             .filter(Transaction.broker == 'BG_SAXO')\
             .group_by(Transaction.operation)\
             .all()
for op, count in ops:
    print(f"{op}: {count}")

print("\n--- CASH TRANSACTIONS ---")
cash_txs = session.query(Transaction)\
                  .filter(Transaction.broker == 'BG_SAXO')\
                  .filter(Transaction.operation.in_(['DEPOSIT', 'WITHDRAW', 'TRANSFER', 'DIVIDEND']))\
                  .all()

for t in cash_txs:
    print(f"{t.timestamp.date()} | {t.operation[:10]} | Amount: {t.total_amount} | Ticker: {t.ticker}")
    
session.close()
