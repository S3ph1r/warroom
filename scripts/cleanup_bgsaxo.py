from pathlib import Path
import sys
# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, Holding

session = SessionLocal()
# Delete old non-normalized transactions
deleted_tx = session.query(Transaction).filter(Transaction.broker == 'BGSAXO').delete()
# Delete old holdings
deleted_h = session.query(Holding).filter(Holding.broker == 'BGSAXO').delete()
session.commit()
print(f"Cleaned {deleted_tx} legacy transactions and {deleted_h} legacy holdings.")
