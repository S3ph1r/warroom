import requests
import json
import re

def get_channel_id_from_oembed(handle):
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/{handle}&format=json"
    print(f"Checking {handle} via oembed: {url}")
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Data: {json.dumps(data, indent=2)}")
            author_url = data.get('author_url', '')
            match = re.search(r'/channel/(UC[\w-]+)', author_url)
            if match:
                return match.group(1)
            else:
                print("No channel ID in author_url")
        else:
            print(f"Failed with status {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return None

handles = ['@MarcoCasario', '@BlackBoxStocks', '@choramedia']
results = {}

for h in handles:
    cid = get_channel_id_from_oembed(h)
    if cid:
        results[h] = cid
        print(f"FOUND: {h} -> {cid}")
    else:
        print(f"FAILED: {h}")

print("-" * 20)
print("Final Results:")
print(json.dumps(results, indent=2))
