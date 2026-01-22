import requests
import re

ids = {
    "MarcoCasario": "UCZp2KqGRkO1goEAaxX5Huyg",
    "BlackBoxStocks": "UC6eiypGm-D04Y2gR2DHsojQ",
    "ChoraMedia": "UCsYN70T0gqR5U_xmWnZKcTQ"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print("Verifying Channel IDs...")
for name, cid in ids.items():
    url = f"https://www.youtube.com/channel/{cid}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"\nChecking {name} ({cid})... Status: {resp.status_code}")
        if resp.status_code == 200:
            # Try to grab the title tag
            title_match = re.search(r'<title>(.*?)</title>', resp.text)
            if title_match:
                print(f"  Title: {title_match.group(1)}")
            else:
                print("  Title tag not found.")
        else:
            print("  Failed to load channel page.")
    except Exception as e:
        print(f"  Error: {e}")
