
import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.forex_service import get_exchange_rate

def check_currencies():
    print("Checking currencies in DB...")
    holdings = get_all_holdings()
    currencies = set([h.get('currency', 'EUR') for h in holdings])
    
    print(f"Found {len(currencies)} currencies: {currencies}")
    print("-" * 40)
    
    for c in currencies:
        if c == 'EUR':
             continue
             
        rate = get_exchange_rate(c, 'EUR')
        print(f"{c} -> EUR: {rate}")
        
        if rate == Decimal('1.0'):
            print(f"  WARNING: {c} returns 1.0! Possible factor for inflation.")
            # Check if likely non-1.0
            if c in ['HKD', 'SEK', 'NOK', 'DKK', 'JPY', 'CNY', 'ZAR', 'TRY', 'MXN']:
                 print(f"  CRITICAL: {c} should NOT be 1.0")

if __name__ == "__main__":
    check_currencies()
