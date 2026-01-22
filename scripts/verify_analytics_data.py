
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/analytics"

def check_endpoint(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    print(f"Checking {url}...")
    try:
        start = datetime.now()
        res = requests.get(url, timeout=15)
        duration = (datetime.now() - start).total_seconds()
        
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Status: 200 (Time: {duration:.2f}s)")
            if isinstance(data, list):
                print(f"   Data Type: List, Count: {len(data)}")
                if data: print(f"   First Item: {data[0]}")
            elif isinstance(data, dict):
                print(f"   Data Type: Dict, Keys: {list(data.keys())}")
                for k, v in data.items():
                    if isinstance(v, list):
                        print(f"   - {k}: {len(v)} points")
                    else:
                        print(f"   - {k}: {v}")
            else:
                print(f"   Data: {data}")
        else:
            print(f"❌ Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

print("--- ANALYTICS DIAGNOSTIC ---")
check_endpoint("history?days=30")
check_endpoint("benchmarks?days=30")
