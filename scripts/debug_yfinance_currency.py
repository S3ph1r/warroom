
import sys
import os
from pathlib import Path
import yfinance as yf

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import to leverage existing mapping logic
from services.price_service_v5 import isin_to_yahoo_ticker

def debug_yfinance():
    targets = [
        ('IE00B0M63516', 'iShares MSCI Brazil'),
        ('IE00B42NKQ00', 'iShares Energy'),
        ('US26740W1099', 'D-Wave')
    ]
    
    print("Debugging Yahoo Finance Metadata...")
    print("-" * 60)
    
    for isin, name in targets:
        print(f"\nChecking: {name} ({isin})")
        ticker_sym = isin_to_yahoo_ticker(isin)
        print(f"Mapped Ticker: {ticker_sym}")
        
        if not ticker_sym:
            print("  -> No ticker found.")
            continue
            
        ticker = yf.Ticker(ticker_sym)
        try:
            info = ticker.info
            currency = info.get('currency')
            price = info.get('regularMarketPrice') or info.get('previousClose')
            exchange = info.get('exchange')
            short_name = info.get('shortName')
            
            print(f"  ShortName: {short_name}")
            print(f"  Exchange:  {exchange}")
            print(f"  Currency:  {currency} (Type: {type(currency)})")
            print(f"  Price:     {price}")
            
            # Check history to be sure
            hist = ticker.history(period='1d')
            if not hist.empty:
                print(f"  Last Close: {hist['Close'].iloc[-1]}")
            else:
                print("  No history found.")
                
        except Exception as e:
            print(f"  Error fetching info: {e}")

if __name__ == "__main__":
    debug_yfinance()
