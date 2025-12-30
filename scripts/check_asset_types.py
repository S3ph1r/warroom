import sys
from pathlib import Path
from collections import Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings

def check_types():
    holdings = get_all_holdings()
    types = [h.get('asset_type') for h in holdings]
    print(Counter(types))
    
    # Print sample of None or Unknown
    for h in holdings:
        if h.get('asset_type') not in ['STOCK', 'ETF', 'CRYPTO', 'CASH', 'COMMODITY']:
             print(f"Unknown Type: {h.get('asset_type')} for {h.get('ticker')}")

if __name__ == "__main__":
    check_types()
