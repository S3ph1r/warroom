"""
Pulizia transazioni anomale dal database
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction
from sqlalchemy import func

session = SessionLocal()

print('='*60)
print('🧹 PULIZIA TRANSAZIONI ANOMALE')
print('='*60)

# 1. Rimuovi transazioni con fiat > 100,000 (anomale)
count_before = session.query(func.count(Transaction.id)).scalar()
print(f'\nTransazioni prima: {count_before}')

# Trova e rimuovi anomale
anomale = session.query(Transaction).filter(Transaction.fiat_amount > 100000).all()
print(f'\nTransazioni con fiat > €100,000: {len(anomale)}')
for t in anomale:
    print(f'  Removing: {t.platform} | {t.ticker_symbol} | €{float(t.fiat_amount):,.2f}')
    session.delete(t)

session.commit()

# 2. Rimuovi anche transazioni UNKNOWN da BG_SAXO (errori di parsing)
unknown_bgsaxo = session.query(Transaction).filter(
    Transaction.platform == 'BG_SAXO',
    Transaction.ticker_symbol == 'UNKNOWN'
).all()
print(f'\nTransazioni BG_SAXO con ticker UNKNOWN: {len(unknown_bgsaxo)}')
for t in unknown_bgsaxo:
    session.delete(t)

session.commit()

# 3. Verifica finale
count_after = session.query(func.count(Transaction.id)).scalar()
total_invested = session.query(func.sum(Transaction.fiat_amount)).filter(
    Transaction.operation_type == 'BUY'
).scalar()

print(f'\n✅ PULIZIA COMPLETATA')
print(f'   Transazioni rimosse: {count_before - count_after}')
print(f'   Transazioni rimanenti: {count_after}')
print(f'   Nuovo totale investito: €{float(total_invested or 0):,.2f}')

# Mostra breakdown per piattaforma
print(f'\n📊 Breakdown per piattaforma:')
by_platform = session.query(
    Transaction.platform,
    func.count(Transaction.id),
    func.sum(Transaction.fiat_amount)
).group_by(Transaction.platform).all()

for platform, count, total in by_platform:
    print(f'   {platform:20} | {count:5} tx | €{float(total or 0):>12,.2f}')

session.close()
