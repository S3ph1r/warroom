import sys
from pathlib import Path
from decimal import Decimal

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.database import SessionLocal
from db.models import Holding

def check_novo():
    db = SessionLocal()
    try:
        print("🔎 Searching for Novo Nordisk in Holdings...")
        holdings = db.query(Holding).filter(Holding.name.ilike("%Novo%")).all()
        
        if not holdings:
            print("❌ No 'Novo' found.")
            # Search by ticker
            tickers = db.query(Holding).filter(Holding.ticker.ilike("%NOVOB%")).all()
            if tickers:
                print("Found via Ticker:")
                holdings = tickers
        
        for h in holdings:
            print(f"ID: {h.id}")
            print(f"Ticker: {h.ticker}")
            print(f"Name: {h.name}")
            print(f"Currency: '{h.currency}'")
            print(f"Broker: {h.broker}")
            print(f"Purchase Price: {h.purchase_price}")
            print(f"Current Price: {h.current_price}")
            print(f"Current Value: {h.current_value}")
            print("---")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_novo()
