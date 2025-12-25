
import requests
import json

try:
    res = requests.get("http://127.0.0.1:8000/api/portfolio")
    if res.status_code == 200:
        data = res.json()
        holdings = data.get("holdings", [])
        print(f"Fetched {len(holdings)} holdings.")
        if holdings:
            h = holdings[0]
            print("Sample Holding Keys:", list(h.keys()))
            print(f"Ticker: {h.get('ticker')}")
            print(f"Current Value: {h.get('current_value')}")
            print(f"Cost Basis: {h.get('cost_basis')}")
            print(f"PnL: {h.get('pnl')}")
            print(f"PnL %: {h.get('pnl_pct')}")
    else:
        print(f"Error: {res.status_code}")
except Exception as e:
    print(f"Exception: {e}")
