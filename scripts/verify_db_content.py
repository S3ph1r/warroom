from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction, Holding
from services.portfolio_service import get_portfolio_summary

db = SessionLocal()
tx_count = db.query(Transaction).count()
h_count = db.query(Holding).count()
revolut_tx = db.query(Transaction).filter(Transaction.broker == "REVOLUT").count()

print(f"--- DB VERIFICATION ---")
print(f"Transactions Total: {tx_count}")
print(f"Revolut Transactions: {revolut_tx}")
print(f"Holdings Total: {h_count}")

# Portfolio Summary
try:
    summary = get_portfolio_summary()
    print(f"\n--- PORTFOLIO SUMMARY ---")
    print(f"Total Value: {summary['total_value']:,.2f} EUR")
    print(f"Brokers: {summary['brokers']}")
except Exception as e:
    print(f"Error getting summary: {e}")

db.close()
