"""Quick database snapshot."""
import sys
sys.path.insert(0, 'd:/Download/Progetto WAR ROOM/warroom')
from db.database import SessionLocal
from db.models import Holding, Transaction
from sqlalchemy import func

session = SessionLocal()

h_count = session.query(func.count(Holding.id)).scalar()
t_count = session.query(func.count(Transaction.id)).scalar()
h_value = session.query(func.sum(Holding.current_value)).scalar() or 0

print('SNAPSHOT BEFORE INGESTION')
print('=' * 50)

brokers_h = session.query(Holding.broker, func.count(Holding.id), func.sum(Holding.current_value)).group_by(Holding.broker).all()
print('Holdings by broker:')
for b, c, v in brokers_h:
    print(f'  {b}: {c} holdings, €{float(v or 0):,.2f}')

brokers_t = session.query(Transaction.broker, func.count(Transaction.id)).group_by(Transaction.broker).all()
print('Transactions by broker:')
for b, c in brokers_t:
    print(f'  {b}: {c} transactions')

print()
print('TOTALS:')
print(f'  Holdings: {h_count}')
print(f'  Transactions: {t_count}')
print(f'  Total Value: €{float(h_value):,.2f}')

session.close()
