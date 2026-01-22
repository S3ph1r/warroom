
import sys
from pathlib import Path
from sqlalchemy import func

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction

session = SessionLocal()
dates = session.query(func.date(Transaction.timestamp), func.count(Transaction.id))\
               .filter(Transaction.broker == 'BG_SAXO')\
               .group_by(func.date(Transaction.timestamp))\
               .all()

print("--- DISTINCT TRANSACTION DATES ---")
for d, count in dates:
    print(f"Date: {d} | Count: {count}")

session.close()
