
import sys
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction

session = SessionLocal()

# Check all operation types
print("--- OPERATION TYPES IN DB ---")
from sqlalchemy import func
ops = session.query(Transaction.operation, func.count(Transaction.id))\
             .filter(Transaction.broker == 'BG_SAXO')\
             .group_by(Transaction.operation)\
             .all()
for op, count in ops:
    print(f"{op}: {count}")

# Look for cash-related transactions
print("\n--- CASH/DEPOSIT TRANSACTIONS ---")
cash_ops = ['DEPOSIT', 'WITHDRAW', 'TRANSFER', 'DIVIDEND', 'INTEREST', 'FEE']
cash_txs = session.query(Transaction)\
                  .filter(Transaction.broker == 'BG_SAXO')\
                  .filter(Transaction.operation.in_(cash_ops))\
                  .all()

if cash_txs:
    for t in cash_txs[:10]:  # Show first 10
        print(f"{t.timestamp.date()} | {t.operation:10} | {t.ticker:15} | {t.total_amount}")
else:
    print("No cash/deposit transactions found.")
    print("(All transactions are likely TRADE type)")

# Calculate theoretical cash balance
print("\n--- THEORETICAL CASH CALCULATION ---")
total_deposits = Decimal(0)
total_withdrawals = Decimal(0)
total_buys = Decimal(0)
total_sells = Decimal(0)

all_txs = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').all()
for t in all_txs:
    if t.operation == 'DEPOSIT':
        total_deposits += abs(t.total_amount)
    elif t.operation == 'WITHDRAW':
        total_withdrawals += abs(t.total_amount)
    elif t.operation in ['BUY', 'TRADE']:
        # Buys reduce cash
        total_buys += abs(t.total_amount)
    elif t.operation == 'SELL':
        total_sells += abs(t.total_amount)

print(f"Deposits:    +{total_deposits}")
print(f"Withdrawals: -{total_withdrawals}")
print(f"Buys:        -{total_buys}")
print(f"Sells:       +{total_sells}")

session.close()
