"""
Debug Price and Currency Conversion for NOVOB and 02050
"""
import sys
sys.path.insert(0, '.')
from services.price_service_v5 import get_yahoo_price, FX_TO_EUR
from db.database import SessionLocal
from db.models import Holding
from decimal import Decimal

def debug_asset(ticker):
    print(f"\n--- Checking {ticker} ---")
    session = SessionLocal()
    h = session.query(Holding).filter(Holding.ticker == ticker).first()
    session.close()
    
    if not h:
        print("Holding not found in DB")
        return

    print(f"DB Data:")
    print(f"  Name: {h.name}")
    print(f"  Qty: {h.quantity}")
    print(f"  Currency: {h.currency}")
    print(f"  Purchase Price: {h.purchase_price} (in {h.currency})")
    
    # Calculate Cost in EUR
    fx_rate = FX_TO_EUR.get(h.currency, 1.0)
    cost_native = h.quantity * h.purchase_price
    cost_eur = cost_native * Decimal(str(fx_rate))
    
    print(f"Cost Analysis:")
    print(f"  FX Rate ({h.currency}->EUR): {fx_rate}")
    print(f"  Cost (Native): {cost_native:.2f} {h.currency}")
    print(f"  Cost (EUR): {cost_eur:.2f} EUR")
    
    # Live Price
    print(f"Live Price Analysis:")
    price, source, success = get_yahoo_price(ticker, h.isin)
    if success:
        val_eur = price * h.quantity
        print(f"  Live Price (EUR/sh): {price:.2f}")
        print(f"  Total Value (EUR): {val_eur:.2f}")
        print(f"  Source: {source}")
        
        # P/L
        pnl = val_eur - cost_eur
        pnl_no_fx = val_eur - cost_native
        
        print(f"P/L Analysis:")
        print(f"  P/L (Correct FX): {pnl:+.2f} EUR")
        print(f"  P/L (Wrong - No FX): {pnl_no_fx:+.2f} EUR (This matches the error?)")
    else:
        print(f"  Failed to fetch price: {source}")

if __name__ == "__main__":
    debug_asset('NOVOB')
    debug_asset('02050')
