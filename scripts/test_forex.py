
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.forex_service import get_exchange_rate, get_rates_for_currencies
from services.price_service_v5 import get_price

def test_forex_fetch():
    print("\n--- Testing Forex Service ---")
    
    # Test USD
    usd_rate = get_exchange_rate("USD", "EUR")
    print(f"USD -> EUR Rate: {usd_rate}")
    if usd_rate > 0.8 and usd_rate < 1.2:
        print("✅ USD rate looks reasonable")
    else:
        print("❌ USD rate looks suspicous")

    # Test GBP
    gbp_rate = get_exchange_rate("GBP", "EUR")
    print(f"GBP -> EUR Rate: {gbp_rate}")
    
    # Test Batch
    print("\nBatch Fetch (USD, GBP, CHF):")
    rates = get_rates_for_currencies(["USD", "GBP", "CHF", "EUR"])
    for curr, rate in rates.items():
        print(f"  {curr}: {rate}")

def test_price_conversion():
    print("\n--- Testing Price Conversion (USD Stock) ---")
    
    ticker = "AAPL"
    print(f"Fetching {ticker} (USD)...")
    price_eur, source, success, change = get_price(ticker, None, "STOCK", None)
    
    print(f"  Price (EUR): {price_eur}")
    print(f"  Source: {source}")
    print(f"  Live: {success}")
    
    if success and price_eur > 100:
        print("✅ AAPL price converted reasonably")
    else:
        print("❌ AAPL price check failed")
        
    print("\n--- Testing Price Conversion (EUR Stock) ---")
    ticker_eu = "LDO.MI"
    print(f"Fetching {ticker_eu} (EUR)...")
    price_eur_eu, source_eu, success_eu, change_eu = get_price(ticker_eu, None, "STOCK", None)
    print(f"  Price (EUR): {price_eur_eu}")
    
    if success_eu and price_eur_eu > 5:
        print("✅ LDO.MI price reasonably")

if __name__ == "__main__":
    test_forex_fetch()
    test_price_conversion()
