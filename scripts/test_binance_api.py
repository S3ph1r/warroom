"""Test Binance Public API for Historical Prices"""
import requests
import time
from datetime import datetime

def get_binance_price(symbol, date_str):
    # date_str: YYYY-MM-DD
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    timestamp_ms = int(dt.timestamp() * 1000)
    
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1d",
        "startTime": timestamp_ms,
        "limit": 1
    }
    
    print(f"Fetching {symbol} for {date_str}...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        # Check if error
        if isinstance(data, dict) and 'code' in data:
            print(f"❌ API Error: {data}")
            return None
            
        if len(data) > 0:
            # kline format: [Open Time, Open, High, Low, Close, Volume, ...]
            close_price = float(data[0][4])
            print(f"✅ {symbol} Price: {close_price} EUR")
            return close_price
        else:
            print(f"⚠️ No data found for {symbol} at {timestamp_ms}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return None

# Test Dates
# BTC existed in 2017
get_binance_price("BTCEUR", "2017-09-21")
get_binance_price("ETHEUR", "2020-01-15")
get_binance_price("BNBEUR", "2021-05-19")

# Test a non-EUR pair? Maybe USDT?
# If BTCEUR didn't exist in 2017 (maybe it was only BTCUSDT), we might need fallback.
# Binance EUR pairs started later.
print("\n--- Testing Fallback (BTCUSDT) ---")
get_binance_price("BTCUSDT", "2017-09-21")
