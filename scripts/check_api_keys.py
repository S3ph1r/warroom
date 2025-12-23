import requests
import json

def check_keys():
    url = "http://127.0.0.1:8000/api/portfolio"
    r = requests.get(url)
    data = r.json()
    holdings = data.get('holdings', [])
    if not holdings:
        print("No holdings")
        return
    
    h = next((x for x in holdings if x['ticker'] == 'XAU'), holdings[0])
    print(f"Keys for {h['ticker']}:")
    for k in sorted(h.keys()):
        print(f"  {k}: {h[k]}")

if __name__ == "__main__":
    check_keys()
