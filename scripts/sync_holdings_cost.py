import sys
from pathlib import Path
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction

def sync_purchase_prices():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).filter(Holding.purchase_price == None).all()
        print(f"Checking {len(holdings)} holdings with missing purchase price...")
        
        updated_count = 0
        for h in holdings:
            # Get all BUY transactions for this asset and broker
            txs = session.query(Transaction).filter(
                Transaction.ticker == h.ticker,
                Transaction.broker == h.broker,
                Transaction.operation == 'BUY'
            ).all()
            
            if txs:
                total_qty = Decimal('0')
                total_cost = Decimal('0')
                for t in txs:
                    total_qty += t.quantity
                    total_cost += t.quantity * t.price
                
                if total_qty > 0:
                    avg_price = total_cost / total_qty
                    h.purchase_price = avg_price
                    updated_count += 1
                    print(f"  Fixed {h.ticker} at {h.broker}: Avg Price = {avg_price:.4f}")
        
        session.commit()
        print(f"Synchronization complete. Updated {updated_count} holdings.")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    sync_purchase_prices()
