
import requests
import json

try:
    resp = requests.get('http://localhost:8000/api/portfolio')
    data = resp.json()
    print("FX_RATES_RESULT:", json.dumps(data.get('fx_rates', 'MISSING')))
except Exception as e:
    print("ERROR:", e)
