
import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings

def compare_portfolio():
    print("Fetching holdings for comparison with BG Saxo screenshots...")
    holdings = get_all_holdings()
    
    # Target specific tickers from the screenshot
    targets = {
        'INTC': 'Intel Corp.',       # USD
        'AMZN': 'Amazon.com Inc.',   # USD
        'NOVO-B.CO': 'Novo Nordisk', # DKK (Check ticker format in DB)
        'NOVOB': 'Novo Nordisk',     # Alternate
        '02050': 'Zhejiang Sanhua',  # HKD
        '2050.HK': 'Zhejiang Sanhua',# Alternate
        'BABA': 'Alibaba',           # EUR (ADR?)
        'AHLA': 'Alibaba',           # BG Saxo Ticker?
    }
    
    # Filter DB holdings
    found_holdings = []
    for h in holdings:
        t = h.get('ticker', '').upper()
        # Loose match
        if t in targets or any(val.upper() in h.get('name', '').upper() for val in targets.values()):
            found_holdings.append(h)
            
    if not found_holdings:
        print("No target holdings found!")
        return

    print(f"Found {len(found_holdings)} matching holdings.")
    
    # Calculate live values
    results = get_live_values_for_holdings(found_holdings)
    
    print("-" * 120)
    print(f"{'Ticker':<12} | {'Name':<20} | {'Qty':<6} | {'Curr':<4} | {'Purch Prc':<10} | {'FX Used':<8} | {'Cost (EUR)':<12} | {'Live (EUR)':<12}")
    print("-" * 120)
    
    for h in found_holdings:
        hid = h['id']
        ticker = h['ticker']
        name = h['name'][:20]
        qty = h['quantity']
        curr = h.get('currency', 'EUR')
        purch_price = h.get('purchase_price', 0)
        
        res = results.get(hid, {})
        fx_rate = res.get('exchange_rate_used', 1.0)
        cost_basis = res.get('cost_basis', 0)
        live_val = res.get('live_value', 0)
        
        print(f"{ticker:<12} | {name:<20} | {qty:<6} | {curr:<4} | {purch_price:<10} | {fx_rate:<8.4f} | {cost_basis:<12.2f} | {live_val:<12.2f}")

if __name__ == "__main__":
    compare_portfolio()
