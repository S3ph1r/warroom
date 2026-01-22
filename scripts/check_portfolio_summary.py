"""
Check Portfolio Summary - Broker by Broker
Aggregates Holdings count and Value by Asset Type.
"""
import sys
from pathlib import Path
from decimal import Decimal
from sqlalchemy import func
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

# Force ASCII art if needed or safe
def format_eur(val):
    return f"{val:,.2f} EUR" # Avoid Euro symbol if problematic, or keep with utf-8 fix

def check_summary():
    session = SessionLocal()
    try:
        brokers = [
            "REVOLUT", 
            "BGSAXO", 
            "TRADE_REPUBLIC", 
            "BINANCE", 
            "IBKR", 
            "SCALABLE_CAPITAL"
        ]
        
        print("=" * 80)
        print("📊 PORTFOLIO SUMMARY (Broker by Broker)")
        print("=" * 80)
        
        grand_total = Decimal(0)
        global_holdings_count = 0
        global_asset_map = defaultdict(Decimal)
        
        for broker in brokers:
            listings = session.query(Holding).filter(Holding.broker == broker).all()
            
            if not listings:
                print(f"\n🔹 {broker}: NO DATA")
                continue
                
            count = len(listings)
            total_val = sum((h.current_value for h in listings), Decimal(0))
            
            # Aggregate by Asset Type
            asset_map = defaultdict(Decimal)
            for h in listings:
                atype = h.asset_type if h.asset_type else "UNKNOWN"
                asset_map[atype] += h.current_value
                global_asset_map[atype] += h.current_value

            print(f"\n🔹 {broker}")
            print(f"   Holdings: {count}")
            print(f"   Total Value: {format_eur(total_val)}")
            print("   Breakdown:")
            for atype, val in asset_map.items():
                print(f"     - {atype:<12}: {format_eur(val)}")
            
            grand_total += total_val
            global_holdings_count += count
            
        print("\n" + "=" * 80)
        print("🌍 GRAND TOTAL")
        print("=" * 80)
        print(f"   Total Holdings: {global_holdings_count}")
        print(f"   Total Value:    {format_eur(grand_total)}")
        print("   Global Breakdown:")
        for atype, val in global_asset_map.items():
             print(f"     - {atype:<12}: {format_eur(val)}")
             
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_summary()
