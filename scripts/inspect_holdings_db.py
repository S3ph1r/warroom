import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

def inspect_db():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).limit(10).all()
        print(f"Inspecting {len(holdings)} holdings...")
        for h in holdings:
            print(f"Ticker: {h.ticker:8} | Qty: {h.quantity:10} | Purchase Price: {h.purchase_price} | Current Price: {h.current_price}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_db()
