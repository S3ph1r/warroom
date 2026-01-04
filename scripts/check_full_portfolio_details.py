"""
Check Full Portfolio Details
Lists every holding with Ticker, ISIN, Quantity, Asset Type, Currency, and Average Price.
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

def check_details():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).order_by(Holding.broker, Holding.asset_type, Holding.ticker).all()
        
        # Header
        print(f"{'BROKER':<18} | {'ASSET':<10} | {'TICKER':<20} | {'ISIN':<14} | {'CUR':<3} | {'AVG_PRC':>10} | {'QTY':>12}")
        print("-" * 105)
        
        current_broker = ""
        
        for h in holdings:
            if h.broker != current_broker:
                print(f"--- {h.broker} ---")
                current_broker = h.broker
                
            isin = h.isin if h.isin else "---"
            atype = h.asset_type if h.asset_type else "UNK"
            ticker = h.ticker if h.ticker else "---"
            curr = h.currency if h.currency else "---"
            avg_prc = h.purchase_price if h.purchase_price else Decimal(0)
            
            # Truncate ticker if too long
            if len(ticker) > 20: ticker = ticker[:17] + "..."
            
            print(f"{h.broker:<18} | {atype:<10} | {ticker:<20} | {isin:<14} | {curr:<3} | {avg_prc:>10.4f} | {h.quantity:>12.6f}")
            
        if not holdings:
            print("No holdings found in database.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_details()
