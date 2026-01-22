
import json

def main():
    with open("scripts/reconciliation_result.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    report = data.get("report", [])
    
    print("\nREVOLUT CALCULATED PORTFOLIO (From History)")
    print(f"{'ASSET':<20} | {'QTY (History)':<15} | {'STATUS'}")
    print("-" * 50)
    
    for item in report:
        asset = item.get("asset")
        hist = item.get("history_net", 0)
        
        # Filter out 0 balance (Sold out)
        if abs(hist) > 0.0001:
            print(f"{asset:<20} | {hist:<15.4f} | Active")
        else:
            # Maybe show recently closed?
            pass

if __name__ == "__main__":
    main()
