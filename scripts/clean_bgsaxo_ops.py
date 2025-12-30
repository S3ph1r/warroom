
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, Holding

session = SessionLocal()
print("Cleaning BG_SAXO data...")

# Count before
t_count = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').count()
h_count = session.query(Holding).filter(Holding.broker == 'BG_SAXO').count()
print(f"Before: {t_count} Transactions, {h_count} Holdings")

# Delete
deleted_t = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').delete()
deleted_h = session.query(Holding).filter(Holding.broker == 'BG_SAXO').delete()

session.commit()
print(f"Deleted: {deleted_t} Transactions, {deleted_h} Holdings")
session.close()
