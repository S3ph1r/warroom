import requests
import json

try:
    print("Fetching from API...")
    r = requests.get("http://localhost:8201/api/intelligence")
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Data type: {type(data)}")
    print(f"Data length: {len(data)}")
    if len(data) > 0:
        print("First item source:", data[0].get('source'))
    else:
        print("Data is empty list.")
except Exception as e:
    print(f"Error: {e}")
