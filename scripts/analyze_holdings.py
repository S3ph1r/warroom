"""
Detailed Holdings Analysis by Broker
Shows holdings with P/L > 100% and compares totals to app values
"""
import sys
sys.path.insert(0, '.')

import importlib
import services.dashboard_price_service as dps
importlib.reload(dps)
from services.portfolio_service import get_all_holdings

holdings = get_all_holdings()
dps._price_cache.clear()

print("Fetching live prices (this may take a minute)...")
live_prices = dps.get_live_prices_for_holdings(holdings)
print("Done!\n")

app_values = {
    'BG_SAXO': 19379,
    'TRADE_REPUBLIC': 2834, 
    'SCALABLE': 4471,
    'IBKR': 418,
    'REVOLUT': 1966,
    'BINANCE': 3331
}

print("=" * 95)
print("ANALISI DETTAGLIATA PER BROKER")
print("=" * 95)

all_problems = []

for broker, app_val in app_values.items():
    broker_holdings = [h for h in holdings if h['broker'] == broker]
    
    total_live = 0
    problem_items = []
    
    for h in broker_holdings:
        hid = h['id']
        ticker = h['ticker']
        isin = h.get('isin', '') or ''
        qty = h['quantity']
        purch_price = h.get('purchase_price') or h.get('current_price') or 0
        
        if hid in live_prices:
            lp = live_prices[hid]
            live_val = lp['live_value']
            live_price = lp['live_price']
            pnl_pct = lp['pnl_pct']
        else:
            live_val = h['current_value']
            live_price = h.get('current_price', 0) or 0
            pnl_pct = 0
        
        total_live += live_val
        
        # Flag problems (P/L > 100% or < -80%)
        if pnl_pct > 100 or pnl_pct < -80:
            problem_items.append({
                'ticker': ticker,
                'isin': isin,
                'qty': qty,
                'purch_price': purch_price,
                'live_price': live_price,
                'live_val': live_val,
                'pnl_pct': pnl_pct
            })
            all_problems.append({
                'broker': broker,
                'ticker': ticker,
                'isin': isin,
                'pnl_pct': pnl_pct,
                'live_price': live_price,
                'purch_price': purch_price
            })
    
    # Broker summary
    diff = total_live - app_val
    pct = (diff / app_val * 100) if app_val else 0
    
    if abs(pct) < 5:
        status = "OK"
    elif abs(pct) < 15:
        status = "CLOSE"
    else:
        status = "MISMATCH"
    
    print(f"\n### {broker} ###")
    print(f"Dashboard: EUR {total_live:>10,.2f}")
    print(f"App:       EUR {app_val:>10,}")
    print(f"Diff:      EUR {diff:>+10,.0f} ({pct:+.1f}%) [{status}]")
    
    # Show problem items
    if problem_items:
        print(f"\n  Holdings problematici (P/L > 100% o < -80%):")
        print(f"  {'Ticker':<10} | {'ISIN':<15} | {'Qty':>8} | {'Purch':>8} | {'Live':>8} | {'Value':>10} | {'P/L':>7}")
        print(f"  " + "-" * 85)
        for p in sorted(problem_items, key=lambda x: abs(x['pnl_pct']), reverse=True):
            print(f"  {p['ticker']:<10} | {p['isin']:<15} | {p['qty']:>8.2f} | {p['purch_price']:>8.2f} | {p['live_price']:>8.2f} | {p['live_val']:>10.2f} | {p['pnl_pct']:>+6.0f}%")

print("\n" + "=" * 95)
print("RIEPILOGO HOLDINGS CON P/L SOSPETTI (> 100%)")
print("=" * 95)

problems_over_100 = [p for p in all_problems if p['pnl_pct'] > 100]
if problems_over_100:
    print(f"\n{'Broker':<12} | {'Ticker':<10} | {'ISIN':<15} | {'Purch':>8} | {'Live':>8} | {'P/L':>7}")
    print("-" * 75)
    for p in sorted(problems_over_100, key=lambda x: x['pnl_pct'], reverse=True):
        print(f"{p['broker']:<12} | {p['ticker']:<10} | {p['isin']:<15} | {p['purch_price']:>8.2f} | {p['live_price']:>8.2f} | {p['pnl_pct']:>+6.0f}%")
else:
    print("\nNessun holding con P/L > 100%!")
    print("I problemi di discrepanza broker sono probabilmente dovuti a:")
    print("  - Documenti datati (BINANCE)")
    print("  - Fluttuazione normale prezzi")

print("\n" + "=" * 95)
print("CONCLUSIONI")
print("=" * 95)

for broker, app_val in app_values.items():
    broker_holdings = [h for h in holdings if h['broker'] == broker]
    total = sum(live_prices[h['id']]['live_value'] if h['id'] in live_prices else h['current_value'] for h in broker_holdings)
    diff = total - app_val
    pct = (diff / app_val * 100) if app_val else 0
    
    if abs(pct) >= 15:
        print(f"{broker}: PROBLEMA - Dashboard EUR {total:,.0f} vs App EUR {app_val:,} ({pct:+.0f}%)")
