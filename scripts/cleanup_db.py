import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.db import get_session
from backend.models import Transaction, Holding

session = get_session()
tx_count = session.query(Transaction).count()
hold_count = session.query(Holding).count()

print(f"Before cleanup: {tx_count} transactions, {hold_count} holdings")

session.query(Transaction).delete()
session.query(Holding).delete()
session.commit()

print("✅ Database cleared successfully")
