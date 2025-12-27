
import json
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    print("FINAL MERGE REVOLUT (Stocks + Crypto + Commodities)")
    
    # 1. Stocks
    stocks_data = load_json("scripts/revolut_stocks_full.json")
    stocks_tx = stocks_data.get("transactions", [])
    
    # 2. Crypto
    crypto_files = list(Path("scripts").glob("revolut_crypto_*.json"))
    crypto_tx = []
    if crypto_files:
        c_data = load_json(crypto_files[0])
        crypto_tx = c_data.get("transactions", [])
        
    # 3. Commodities
    commodities_data = load_json("scripts/revolut_commodities_only.json")
    comm_tx = commodities_data.get("transactions", [])
    
    all_tx = stocks_tx + crypto_tx + comm_tx
    print(f"Counts: Stocks={len(stocks_tx)}, Crypto={len(crypto_tx)}, Comm={len(comm_tx)}")
    print(f"Total: {len(all_tx)}")
    
    merged_path = "scripts/revolut_full_reconciled.json"
    with open(merged_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": all_tx}, f, indent=2)
        
    print(f"Saved to {merged_path}")

if __name__ == "__main__":
    main()
