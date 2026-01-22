
import sys
import os
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings
from services.forex_service import get_exchange_rate

def inspect_scalable():
    print("Fetching Scalable Capital holdings...")
    holdings = get_all_holdings()
    scalable_holdings = [h for h in holdings if "SCALABLE" in str(h.get("broker", "")).upper()]
    
    if not scalable_holdings:
        print("No Scalable Capital holdings found!")
        return

    print(f"Found {len(scalable_holdings)} holdings.")
    
    results = get_live_values_for_holdings(scalable_holdings)
    
    for h in scalable_holdings:
        hid = h['id']
        ticker = h['ticker']
        isin = h.get('isin')
        qty = h['quantity']
        curr = h.get('currency')
        
        res = results.get(hid, {})
        live_price = res.get('live_price')
        live_val = res.get('live_value')
        native_val = res.get('native_current_value')
        fx_used = res.get('exchange_rate_used')
        source = res.get('source')
        
        print("-" * 50)
        print(f"Checking: {ticker} (ISIN: {isin})")
        print(f"  DB Data: Qty={qty}, Curr={curr}")
        print(f"  Live Data: Price (EUR)={live_price}, Source={source}")
        print(f"  Live Value (EUR)={live_val}")
        print(f"  Native Value={native_val} (FX Used: {fx_used})")
        
        # Manual Check
        print(f"  MANUAL CALC: {qty} * {live_price} = {float(qty) * float(live_price) if live_price else 0}")

if __name__ == "__main__":
    inspect_scalable()
