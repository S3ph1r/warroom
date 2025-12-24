import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/analytics"

def test_save_snapshot():
    print("\n--- Testing POST /snapshot ---")
    try:
        response = requests.post(f"{BASE_URL}/snapshot")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"Error: {e}")
    return False

def test_get_latest():
    print("\n--- Testing GET /latest ---")
    try:
        response = requests.get(f"{BASE_URL}/latest")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_get_history():
    print("\n--- Testing GET /history ---")
    try:
        response = requests.get(f"{BASE_URL}/history?days=30")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"History items: {len(data)}")
        if len(data) > 0:
            print(f"First item: {data[0]}")
    except Exception as e:
        print(f"Error: {e}")

def test_get_risk_metrics():
    print("\n--- Testing GET /risk-metrics ---")
    try:
        response = requests.get(f"{BASE_URL}/risk-metrics")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if test_save_snapshot():
        test_get_latest()
        test_get_history()
        test_get_risk_metrics()
    else:
        print("Skipping subsequent tests due to snapshot failure.")
