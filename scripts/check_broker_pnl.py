
import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.getcwd())

from backend.main import build_portfolio_data
from services.price_service_v5 import clear_cache

def check_pnl():
    # Clear cache to ensure fresh prices specially for failing tickers
    clear_cache()
    
    print("--- Fetching Portfolio Data ---")
    data = build_portfolio_data()
    
    print(f"\nTotal P&L: {data['total_pnl']:,.2f} EUR")
    
    brokers = data.get("broker_totals", {})
    
    print("\n--- Broker P&L ---")
    for name, stats in brokers.items():
        pnl = stats.get("pnl", 0)
        print(f"{name:<15}: {pnl:,.2f} EUR")

    print("\n--- Asset Breakdown (Worst 15 P&L) ---")
    all_h = data.get("holdings", [])
    # Sort by P&L ascending (worst first)
    all_h.sort(key=lambda x: x.get("pnl", 0))
    
    for h in all_h[:15]:
        b = h.get('broker')
        t = h.get('ticker')
        val = h.get('current_value')
        cost = h.get('cost_basis')
        pnl = h.get('pnl')
        price = h.get('live_price')
        
        if b in ["TRADE_REPUBLIC", "REVOLUT", "BG_SAXO", "SCALABLE"]:
             print(f"{b:<15} {t:<10} Val:{val:>8.1f} Cost:{cost:>8.1f} P&L:{pnl:>8.1f} (Live:{price:.2f})")

if __name__ == "__main__":
    check_pnl()
