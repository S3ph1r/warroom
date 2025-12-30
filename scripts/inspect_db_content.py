import sys
from pathlib import Path
from sqlalchemy import func

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.database import SessionLocal
from db.models import Transaction, Holding

def inspect_db():
    db = SessionLocal()
    try:
        # 1. TRANSACTIONS
        tx_count = db.query(Transaction).count()
        print(f"📊 TRANSACTIONS TABLE: {tx_count} records")
        
        # Breakdown by Operation
        stats = db.query(Transaction.operation, func.count(Transaction.id)).group_by(Transaction.operation).all()
        for op, count in stats:
            print(f"   - {op}: {count}")

        print("\n   Last 3 Transactions:")
        last_txs = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(3).all()
        for t in last_txs:
            print(f"     [{t.timestamp.date()}] {t.operation} {t.ticker} Qty={t.quantity} ISIN={t.isin if hasattr(t, 'isin') else 'N/A'}")

        # 2. HOLDINGS
        h_count = db.query(Holding).count()
        print(f"\n💼 HOLDINGS TABLE: {h_count} active assets")
        
        # Breakdown by Asset Type
        h_stats = db.query(Holding.asset_type, func.count(Holding.id)).group_by(Holding.asset_type).all()
        for at, count in h_stats:
            print(f"   - {at}: {count}")

        print("\n   Top 5 Holdings (by Quantity):")
        top_h = db.query(Holding).order_by(Holding.quantity.desc()).limit(5).all()
        for h in top_h:
            print(f"     {h.ticker} ({h.name}) | Qty: {h.quantity} | ISIN: {h.isin} | Broker: {h.broker}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_db()
