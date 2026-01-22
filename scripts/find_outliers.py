
import sys
import os
from pathlib import Path
from decimal import Decimal

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings

def find_outliers():
    print("Scanning for P&L outliers...")
    holdings = get_all_holdings()
    results = get_live_values_for_holdings(holdings)
    
    outliers = []
    
    for h in holdings:
        hid = h['id']
        name = h.get('name', h.get('ticker', 'Unknown'))
        broker = h.get('broker', 'Unknown')
        
        res = results.get(hid, {})
        pnl_pct = res.get('pnl_pct', 0)
        current_val = res.get('live_value', 0)
        cost = res.get('cost_basis', 0)
        
        # We are looking for high positive outliers (5x value implies +400% P&L)
        if pnl_pct > 200 or pnl_pct < -90:
             outliers.append({
                 'name': name,
                 'broker': broker,
                 'pnl_pct': pnl_pct,
                 'val': current_val,
                 'cost': cost,
                 'ticker': h.get('ticker'),
                 'currency': h.get('currency'),
                 'price_src': res.get('source')
             })
             
    # Sort by P&L desc
    outliers.sort(key=lambda x: x['pnl_pct'], reverse=True)
    
    print(f"Found {len(outliers)} outliers (>200% or <-90%):")
    for o in outliers:
        print(f"[{o['broker']}] {o['name']} ({o['ticker']}): {o['pnl_pct']:.1f}% | Cost: {o['cost']:.1f} -> Val: {o['val']:.1f} | Curr: {o['currency']}")

if __name__ == "__main__":
    find_outliers()
