import requests
import json
import time

API_URL = "http://127.0.0.1:8000/api/logs"

def watch_logs():
    print(f"--- Watching Logs from {API_URL} ---")
    last_count = 0
    try:
        while True:
            resp = requests.get(API_URL)
            if resp.status_code == 200:
                logs = resp.json().get('logs', [])
                if len(logs) > last_count:
                    for line in logs[last_count:]:
                        print(line)
                    last_count = len(logs)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping log watch.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    watch_logs()
