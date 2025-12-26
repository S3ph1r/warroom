
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database import SessionLocal
from db.models import Transaction, Holding

def inspect():
    db = SessionLocal()
    try:
        print("--- Recent Transactions ---")
        txs = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(10).all()
        for tx in txs:
            print(f"ID: {tx.id} | Date: {tx.timestamp} | Broker: '{tx.broker}' | Ticker: '{tx.ticker}' | Op: '{tx.operation}' | Qty: {tx.quantity} | Price: {tx.price} | Curr: {tx.currency}")

        print("\n--- Current Holdings (Cash) ---")
        cash = db.query(Holding).filter(Holding.asset_type == "CASH").all()
        for h in cash:
            print(f"Broker: '{h.broker}' | Curr: '{h.currency}' | Qty: {h.quantity} | Val: {h.current_value}")

        print("\n--- Current Holdings (NVDA) ---")
        nvda = db.query(Holding).filter(Holding.ticker == "NVDA").all()
        for h in nvda:
            print(f"Broker: '{h.broker}' | Ticker: '{h.ticker}' | Qty: {h.quantity} | Val: {h.current_value}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect()
