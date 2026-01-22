"""
Analisi transazioni per trovare valori anomali
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction
from sqlalchemy import func, desc

session = SessionLocal()

print('='*60)
print('🔍 ANALISI TRANSAZIONI WAR ROOM')
print('='*60)

# Totale transazioni
total = session.query(func.count(Transaction.id)).scalar()
print(f'\n📊 Totale transazioni: {total}')

# Per piattaforma
print('\n📈 Per piattaforma:')
by_platform = session.query(
    Transaction.platform,
    func.count(Transaction.id),
    func.sum(Transaction.fiat_amount)
).group_by(Transaction.platform).all()

for platform, count, total_fiat in by_platform:
    print(f'  {platform:20} | {count:5} tx | €{float(total_fiat or 0):>15,.2f}')

# Per tipo operazione
print('\n📋 Per tipo operazione:')
by_type = session.query(
    Transaction.operation_type,
    func.count(Transaction.id),
    func.sum(Transaction.fiat_amount)
).group_by(Transaction.operation_type).all()

for op_type, count, total_fiat in by_type:
    print(f'  {op_type:15} | {count:5} tx | €{float(total_fiat or 0):>15,.2f}')

# Top 20 valori più alti
print('\n⚠️ TOP 20 TRANSAZIONI CON VALORI PIÙ ALTI:')
print('-'*80)
top_high = session.query(Transaction).order_by(desc(Transaction.fiat_amount)).limit(20).all()
for t in top_high:
    print(f'{t.platform:15} | {t.ticker_symbol:10} | {t.operation_type:10} | €{float(t.fiat_amount):>12,.2f} | Qty: {float(t.quantity):.6f}')

# Cerca transazioni con valori > 10000
print('\n🚨 TRANSAZIONI > €10,000:')
big_ones = session.query(Transaction).filter(Transaction.fiat_amount > 10000).order_by(desc(Transaction.fiat_amount)).all()
print(f'Trovate: {len(big_ones)}')
for t in big_ones[:30]:
    print(f'{t.timestamp.strftime("%Y-%m-%d")} | {t.platform:15} | {t.ticker_symbol:10} | {t.operation_type:10} | €{float(t.fiat_amount):>12,.2f}')

# Statistiche per ticker con valori più alti
print('\n📊 TOP 10 TICKER PER INVESTITO:')
by_ticker = session.query(
    Transaction.ticker_symbol,
    func.sum(Transaction.fiat_amount)
).filter(
    Transaction.operation_type == 'BUY'
).group_by(Transaction.ticker_symbol).order_by(desc(func.sum(Transaction.fiat_amount))).limit(10).all()

for ticker, total in by_ticker:
    print(f'  {ticker:15} | €{float(total or 0):>15,.2f}')

session.close()
