
import requests

try:
    resp = requests.get('http://localhost:8000/api/logs')
    data = resp.json()
    print("ALL LOGS:")
    for line in data.get('logs', []):
        print(line)
except Exception as e:
    print("ERROR:", e)
