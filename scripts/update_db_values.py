import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding
from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings
import logging
logging.basicConfig(level=logging.DEBUG)

def update_db_values():
    print("--- UPDATING DB VALUES ---")
    
    # 1. Get Holdings (Dicts)
    holdings_dicts = get_all_holdings()
    print(f"Holdings: {len(holdings_dicts)}")
    
    # 2. Get Live Prices
    print("Fetching live prices...")
    live_data = get_live_values_for_holdings(holdings_dicts)
    
    # 3. Update DB
    db = SessionLocal()
    try:
        updated_count = 0
        total_value = Decimal("0")
        
        for h_dict in holdings_dicts:
            hid = h_dict['id']
            if hid not in live_data: continue
            
            stats = live_data[hid]
            live_val = stats['live_value']
            live_price = stats['live_price']
            
            # Find in DB
            h_row = db.query(Holding).filter(Holding.id == hid).first()
            if h_row:
                h_row.current_value = Decimal(str(live_val))
                h_row.current_price = Decimal(str(live_price))
                h_row.native_current_value = Decimal(str(stats.get('native_current_value', 0)))
                # h_row.exchange_rate_used = Decimal(str(stats.get('exchange_rate_used', 1)))
                
                updated_count += 1
                total_value += h_row.current_value
        
        db.commit()
        print(f"✅ Updated {updated_count} holdings in DB.")
        print(f"💰 Total Portfolio Value: €{total_value:,.2f}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_db_values()
