import sys
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings

def verify_service():
    print("--- VERIFYING SERVICE OUTPUT ---")
    holdings = get_all_holdings()
    print(f"Loaded {len(holdings)} holdings from DB.")
    
    # Filter for interesting ones
    # Check NVDA, BTC, ETH, and one that might be broken
    targets = ['NVDA', 'BTC', 'ETH', 'NOW', 'TSLA', 'AAPL', 'SOL']
    
    print("\nFetching Live Values...")
    results = get_live_values_for_holdings(holdings)
    
    print(f"\nResults Count: {len(results)}")
    
    found_count = 0
    zero_count = 0
    
    for h in holdings:
        hid = h['id']
        ticker = h.get('ticker')
        atype = h.get('asset_type')
        
        if hid not in results:
            print(f"MISSING: {ticker}")
            continue
            
        res = results[hid]
        val = res['live_value']
        source = res['source']
        price = res['live_price']
        
        if val > 0:
            found_count += 1
        else:
            zero_count += 1
            
        if ticker in targets or val > 0:
            print(f"{ticker:<10} ({atype:<8}): €{val:>10,.2f} | Price: {price:>8.2f} | Src: {source}")
            
    print(f"\nSUMMARY: Found Value: {found_count}, Zero Value: {zero_count}")

if __name__ == "__main__":
    verify_service()
