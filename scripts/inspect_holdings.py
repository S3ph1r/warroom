import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings

def inspect():
    holdings = get_all_holdings()
    print(f"Total Holdings: {len(holdings)}")
    
    zeros = 0
    bad_tickers = []
    
    for h in holdings:
        val = h.get('current_value', 0)
        ticker = h.get('ticker')
        name = h.get('name')
        
        if val <= 0:
            zeros += 1
            bad_tickers.append(f"{ticker} ({name})")
            
    print(f"Zero Value Holdings: {zeros}")
    if bad_tickers:
        print("Sample Bad Tickers (First 20):")
        for t in bad_tickers[:20]:
            print(f" - {t}")

if __name__ == "__main__":
    inspect()
