
import json

def main():
    with open("scripts/revolut_commodities.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    all_tx = data.get("transactions", [])
    print(f"Total Transactions: {len(all_tx)}")
    
    commodities = [tx for tx in all_tx if tx.get("asset") in ["XAU", "XAG", "Gold", "Silver", "ORO", "ARGENTO"]]
    
    print(f"Commodities Found: {len(commodities)}")
    for c in commodities:
        print(c)

    # Save ONLY commodities to merge? 
    # Or merge everything? 
    # If we merge Cash transactions, we might get "Cash" asset which logic verifies.
    # But user asked for Commodities.
    
    with open("scripts/revolut_commodities_only.json", 'w') as f:
        json.dump({"transactions": commodities}, f, indent=2)

if __name__ == "__main__":
    main()
