import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding

def broker_summary():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).all()
        print(f"Total Holdings: {len(holdings)}")
        
        brokers = {}
        for h in holdings:
            b = h.broker or 'N/A'
            if b not in brokers:
                brokers[b] = {'count': 0, 'value': Decimal('0'), 'qty_neg': 0, 'qty_pos': 0}
            brokers[b]['count'] += 1
            brokers[b]['value'] += h.current_value or Decimal('0')
            if h.quantity and h.quantity < 0:
                brokers[b]['qty_neg'] += 1
            elif h.quantity and h.quantity > 0:
                brokers[b]['qty_pos'] += 1
        
        print("\nBroker Summary:")
        total = Decimal('0')
        for b, d in sorted(brokers.items()):
            print(f"  {b}: {d['count']} holdings (pos:{d['qty_pos']}, neg:{d['qty_neg']}), €{d['value']:.2f}")
            total += d['value']
        
        print(f"\nTOTAL: €{total:.2f}")
        
    finally:
        session.close()

if __name__ == "__main__":
    broker_summary()
