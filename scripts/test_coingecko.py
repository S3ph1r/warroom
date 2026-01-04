"""Test CoinGecko Historical Data"""
import requests
import time
from datetime import datetime

def get_coingecko_price(coin_id, date_str):
    # date_str format: dd-mm-yyyy
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
    params = {
        "date": date_str,
        "localization": "false"
    }
    
    print(f"Fetching {coin_id} for {date_str}...")
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'market_data' in data and 'current_price' in data['market_data']:
                price = data['market_data']['current_price'].get('eur')
                print(f"✅ Price: {price} EUR")
                return price
            else:
                print(f"⚠️ No market data found: {data.keys()}")
        elif resp.status_code == 429:
            print("❌ Rate Limit Hit (429)")
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return None

# Test Dates (Format: dd-mm-yyyy)
# 2017-09-21
get_coingecko_price("bitcoin", "21-09-2017")
time.sleep(2) # Be nice to API
get_coingecko_price("ethereum", "15-01-2020")
time.sleep(2)
get_coingecko_price("binancecoin", "19-05-2021")
