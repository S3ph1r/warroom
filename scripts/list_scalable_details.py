
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings

def list_scalable_details():
    try:
        print("Fetching full Scalable Capital ledger...")
        holdings = get_all_holdings()
        scalable = [h for h in holdings if "SCALABLE" in str(h.get("broker", "")).upper()]
        
        print(f"Total Scalable Holdings in DB: {len(scalable)}")
        print("-" * 140)
        print(f"{'Ticker':<12} | {'ISIN':<14} | {'Name':<35} | {'Qty':<8} | {'Created At':<20} | {'Updated At':<20}")
        print("-" * 140)
        
        # Sort by Name
        scalable.sort(key=lambda x: x.get('name', ''))
        
        for h in scalable:
            ticker = h.get('ticker', 'N/A')
            isin = h.get('isin', 'N/A') or 'N/A'
            name = h.get('name', 'Unknown')[:35]
            qty = h.get('quantity', 0)
            
            created = h.get('created_at')
            updated = h.get('updated_at')
            
            # Format dates if they are string or datetime
            c_str = str(created)[:19] if created else "N/A"
            u_str = str(updated)[:19] if updated else "N/A"
            
            print(f"{ticker:<12} | {isin:<14} | {name:<35} | {qty:<8} | {c_str:<20} | {u_str:<20}")

    except Exception as e:
        print(f"Error listing holdings: {e}")

if __name__ == "__main__":
    list_scalable_details()
