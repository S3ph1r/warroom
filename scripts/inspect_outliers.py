
import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings

def inspect_outliers():
    print("Inspecting specific outliers...")
    holdings = get_all_holdings()
    
    targets = ['IE00B0M63516', 'IE00B42NKQ00', 'US26740W1099']
    
    target_holdings = [h for h in holdings if h.get('isin') in targets]
    results = get_live_values_for_holdings(target_holdings)
    
    for h in target_holdings:
        hid = h['id']
        isin = h.get('isin')
        ticker = h.get('ticker')
        res = results.get(hid, {})
        
        print("-" * 60)
        print(f"ISIN: {isin} | Ticker: {ticker} | Name: {h.get('name')}")
        print(f"DB: Qty={h.get('quantity')}, Price={h.get('purchase_price')}, Curr={h.get('currency')}")
        print(f"Live: Price={res.get('live_price')}, Source={res.get('source')}")
        print(f"      Val={res.get('live_value')}, Cost={res.get('cost_basis')}")
        print(f"      FX Used: {res.get('exchange_rate_used')}, Native Prc Source: {res.get('source')}")

if __name__ == "__main__":
    inspect_outliers()
