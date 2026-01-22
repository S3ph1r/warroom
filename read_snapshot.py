import json
from pathlib import Path

def read_snapshot():
    p = Path("data/portfolio_snapshot.json")
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Find TR in by_broker or holdings
            print(f"Total Value: {data.get('total_value')}")
            print(f"Brokers: {data.get('brokers')}")
            print(f"By Broker: {data.get('by_broker')}")
            
            tr_holdings = [h for h in data.get('holdings', []) if h.get('broker') == 'TRADE_REPUBLIC']
            print(f"TR Holdings in Snapshot: {len(tr_holdings)}")
            for h in tr_holdings:
                print(f"  - {h.get('ticker')}: {h.get('quantity')} (Value: {h.get('current_value')})")
    else:
        print("Snapshot not found.")

if __name__ == "__main__":
    read_snapshot()
