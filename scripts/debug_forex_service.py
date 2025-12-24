
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.forex_service import get_exchange_rate

def test_service():
    print("Testing Forex Service via Script...")
    try:
        rate = get_exchange_rate("EUR", "USD")
        print(f"Result for EUR->USD: {rate}")
        
        rate_gbp = get_exchange_rate("EUR", "GBP")
        print(f"Result for EUR->GBP: {rate_gbp}")
        
        rate_chf = get_exchange_rate("EUR", "CHF")
        print(f"Result for EUR->CHF: {rate_chf}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_service()
