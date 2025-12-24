
import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings

def debug_scalable():
    print("Fetching Scalable Capital holdings...")
    holdings = get_all_holdings()
    scalable = [h for h in holdings if "SCALABLE" in str(h.get("broker", "")).upper()]
    
    print(f"Found {len(scalable)} Scalable holdings.")
    
    # Calculate live values
    results = get_live_values_for_holdings(scalable)
    
    total_val = 0.0
    
    # Sort by value desc
    holdings_with_val = []
    for h in scalable:
        hid = h['id']
        res = results.get(hid, {})
        val = res.get('live_value', 0.0)
        holdings_with_val.append((h, val, res))
        total_val += val

    print(f"Total Scalable Value: {total_val:.2f} EUR")
    print("-" * 100)
    print(f"{'Ticker':<12} | {'Name':<30} | {'Qty':<6} | {'Price':<10} | {'Value (EUR)':<12} | {'Source'}")
    print("-" * 100)

    # Sort descending by value
    holdings_with_val.sort(key=lambda x: x[1], reverse=True)
    
    for h, val, res in holdings_with_val:
        ticker = h.get('ticker')
        name = h.get('name', '')[:30]
        qty = h.get('quantity')
        price = res.get('live_price', 0)
        source = res.get('source', '')
        
        print(f"{ticker:<12} | {name:<30} | {qty:<6} | {price:<10.2f} | {val:<12.2f} | {source}")

if __name__ == "__main__":
    debug_scalable()
