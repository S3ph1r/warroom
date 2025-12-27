
import json
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    print("Merging Revolut Data...")
    
    # Load Stocks
    stocks_data = load_json("scripts/revolut_stocks_full.json")
    stocks_tx = stocks_data.get("transactions", [])
    print(f"Stocks: {len(stocks_tx)}")
    
    # Load Crypto
    # Find the exact filename for crypto
    crypto_files = list(Path("scripts").glob("revolut_crypto_*.json"))
    crypto_tx = []
    if crypto_files:
        c_data = load_json(crypto_files[0])
        crypto_tx = c_data.get("transactions", [])
        print(f"Crypto: {len(crypto_tx)}")
    else:
        print("No Crypto file found")
        
    # Combine
    all_tx = stocks_tx + crypto_tx
    print(f"Total Combined: {len(all_tx)}")
    
    merged_path = "scripts/revolut_final.json"
    with open(merged_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": all_tx}, f, indent=2)
        
    print(f"Saved to {merged_path}")

if __name__ == "__main__":
    main()
