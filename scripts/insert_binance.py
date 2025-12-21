"""
Insert Binance holdings from user-provided SPOT+EARN data
Run this script to update Binance holdings in DB
"""
import sys
sys.path.insert(0, '.')
from db.database import SessionLocal
from db.models import Holding
from datetime import datetime, timezone

# User-provided data (2025-12-21)
BINANCE_HOLDINGS = [
    # SPOT
    {'ticker': 'ETH', 'quantity': 0.21840415, 'value': 555, 'type': 'CRYPTO'},
    {'ticker': 'BTC', 'quantity': 0.005, 'value': 377, 'type': 'CRYPTO'},
    {'ticker': 'HBAR', 'quantity': 794.494, 'value': 77, 'type': 'CRYPTO'},
    {'ticker': 'IOTA', 'quantity': 807.07431186, 'value': 62, 'type': 'CRYPTO'},
    {'ticker': 'FET', 'quantity': 111.16659955, 'value': 20, 'type': 'CRYPTO'},
    {'ticker': 'TON', 'quantity': 10.3753279, 'value': 13, 'type': 'CRYPTO'},
    {'ticker': 'EUR', 'quantity': 5.90890955, 'value': 6, 'type': 'CASH'},
    {'ticker': 'FF', 'quantity': 11.93472616, 'value': 1, 'type': 'CRYPTO'},
    # EARN
    {'ticker': 'BNB', 'quantity': 1.32636288, 'value': 966, 'type': 'CRYPTO'},
    {'ticker': 'USDC', 'quantity': 856.07331611, 'value': 731, 'type': 'CASH'},
    {'ticker': 'XRP', 'quantity': 157.56655958, 'value': 261, 'type': 'CRYPTO'},
    {'ticker': 'SOL', 'quantity': 2.05578801, 'value': 221, 'type': 'CRYPTO'},
    {'ticker': 'TRX', 'quantity': 127.74608762, 'value': 31, 'type': 'CRYPTO'},
    {'ticker': 'ENA', 'quantity': 12.95572156, 'value': 2, 'type': 'CRYPTO'},
]

def main():
    session = SessionLocal()
    
    try:
        # 1. Delete all existing BINANCE holdings
        deleted = session.query(Holding).filter(Holding.broker == 'BINANCE').delete()
        print(f"Deleted {deleted} old BINANCE holdings")
        
        # 2. Insert new holdings
        for h in BINANCE_HOLDINGS:
            price_per_unit = h['value'] / h['quantity'] if h['quantity'] > 0 else h['value']
            
            holding = Holding(
                broker='BINANCE',
                ticker=h['ticker'],
                name=h['ticker'],
                asset_type=h['type'],
                quantity=h['quantity'],
                purchase_price=price_per_unit,
                current_price=price_per_unit,
                current_value=h['value'],
                currency='EUR',
                source_document='manual_update_2025-12-21',
                last_updated=datetime.now(timezone.utc)
            )
            session.add(holding)
            print(f"  Added: {h['ticker']:6} | Qty: {h['quantity']:>12.4f} | Val: EUR {h['value']:>6}")
        
        session.commit()
        
        # 3. Verify
        total = session.query(Holding).filter(Holding.broker == 'BINANCE').count()
        total_value = sum([h['value'] for h in BINANCE_HOLDINGS])
        print(f"\nInserted {total} BINANCE holdings")
        print(f"Total value: EUR {total_value:,.0f}")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    main()
