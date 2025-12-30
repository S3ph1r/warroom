import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Holding, Transaction

session = SessionLocal()
h_count = session.query(Holding).filter(Holding.broker == "BG_SAXO").count()
t_count = session.query(Transaction).filter(Transaction.broker == "BG_SAXO").count()
print(f"DB VERIFICATION:\nHoldings: {h_count}\nTransactions: {t_count}")
session.close()
