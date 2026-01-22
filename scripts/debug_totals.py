import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction
from sqlalchemy import func

def debug_totals():
    session = SessionLocal()
    print('='*50)
    print('📊 DATABASE TOTALS BY PLATFORM')
    print('='*50)

    results = session.query(
        Transaction.platform,
        func.count(Transaction.id),
        func.sum(Transaction.fiat_amount)
    ).group_by(Transaction.platform).all()

    grand_total = 0
    for platform, count, total in results:
        if total is None: total = 0
        print(f'{platform:<20} | {count:>5} tx | €{total:,.2f}')
        grand_total += total

    print('-'*50)
    print(f'GRAND TOTAL: €{grand_total:,.2f}')
    session.close()

if __name__ == "__main__":
    debug_totals()
