import requests
import json

def check_portfolio():
    url = "http://127.0.0.1:8000/api/portfolio"
    try:
        print(f"Calling {url}...")
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Error: {r.status_code}")
            return
        
        data = r.json()
        holdings = data.get('holdings', [])
        
        # Check for non-zero day changes
        non_zero_changes = [h for h in holdings if h.get('day_change_pct', 0) != 0]
        # Check for non-zero cost basis
        non_zero_cost = [h for h in holdings if h.get('cost_basis', 0) > 0]
        
        print(f"Total holdings: {len(holdings)}")
        print(f"Holdings with non-zero 1D%: {len(non_zero_changes)}")
        print(f"Holdings with non-zero Cost Basis: {len(non_zero_cost)}")
        
        if holdings:
            print("\nSample 1D & Avg Data (First 10):")
            for h in holdings[:10]:
                ticker = h.get('ticker')
                qty = h.get('quantity', 1)
                cost = h.get('cost_basis', 0)
                avg = cost / qty if qty else 0
                day_pct = h.get('day_change_pct', 0)
                print(f"  {ticker:8} | Avg: {avg:10.2f} | 1D%: {day_pct:6.2f}%")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_portfolio()
