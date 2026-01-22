"""Test historical price fetching with yfinance"""
import yfinance as yf
from datetime import datetime
import pandas as pd

def test_historical_price(ticker, date_str):
    print(f"\n--- Testing {ticker} on {date_str} ---")
    try:
        # yfinance expects date range. For a single day, we ask for start=day, end=day+1
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        end_date_obj = date_obj + pd.Timedelta(days=1)
        
        # Download data
        data = yf.download(ticker, start=date_str, end=end_date_obj.strftime("%Y-%m-%d"), progress=False)
        
        if not data.empty:
            print(f"✅ Found data:")
            print(data[['Close']].to_string())
            price = data['Close'].iloc[0]
            # Handle if it's a Series or scalar
            try:
                price = float(price.iloc[0]) # if multi-index
            except:
                price = float(price)
            print(f"   Price: {price} EUR")
        else:
            print(f"❌ No data found for {ticker}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Test simple ones
test_historical_price("BTC-EUR", "2017-09-21") # User's first tx date
test_historical_price("ETH-EUR", "2020-01-15")
test_historical_price("BNB-EUR", "2021-05-19")

# Test obscure ones?
test_historical_price("WTC-EUR", "2017-09-21") # Appears in sample
