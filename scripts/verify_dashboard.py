"""
Verify Dashboard Values vs App Values
"""
import sys
sys.path.insert(0, '.')

import importlib
import services.dashboard_price_service as dps
importlib.reload(dps)

from services.portfolio_service import get_all_holdings

holdings = get_all_holdings()

# User-provided app values
app_values = {
    'BG_SAXO': 19379,
    'TRADE_REPUBLIC': 2834,
    'SCALABLE': 4471,
    'IBKR': 418,
    'REVOLUT': 1966,
    'BINANCE': 3331,
}

# Clear cache and get fresh prices
dps._price_cache.clear()
live_prices = dps.get_live_prices_for_holdings(holdings)

print("=" * 75)
print("CONFRONTO VALORI DASHBOARD vs VALORI APP")
print("=" * 75)
print()

# Calculate totals by broker with live prices
by_broker = {}
for h in holdings:
    broker = h['broker']
    hid = h['id']
    value = live_prices[hid]['live_value'] if hid in live_prices else h['current_value']
    by_broker[broker] = by_broker.get(broker, 0) + value

# Print comparison
print(f"{'Broker':<15} | {'Dashboard':>12} | {'App':>10} | {'Differenza':>12} | Status")
print("-" * 75)

for broker, app_val in app_values.items():
    dash_val = by_broker.get(broker, 0)
    diff = dash_val - app_val
    pct = (diff / app_val * 100) if app_val else 0
    
    if abs(pct) < 5:
        status = "OK"
    elif abs(pct) < 15:
        status = "CLOSE"
    elif abs(pct) < 30:
        status = "MISMATCH"
    else:
        status = "MAJOR"
    
    print(f"{broker:<15} | EUR {dash_val:>8,.0f} | {app_val:>9,} | {diff:>+10,.0f} ({pct:>+5.1f}%) | {status}")

print("-" * 75)
total_dash = sum(by_broker.values())
total_app = sum(app_values.values())
total_diff = total_dash - total_app
total_pct = (total_diff / total_app * 100)
print(f"{'TOTALE':<15} | EUR {total_dash:>8,.0f} | {total_app:>9,} | {total_diff:>+10,.0f} ({total_pct:>+5.1f}%)")

print()
print("=" * 75)
print("HOLDINGS CON P/L SOSPETTI (>100% o <-50%)")
print("=" * 75)

suspicious = []
for h in holdings:
    hid = h['id']
    if hid in live_prices:
        pnl_pct = live_prices[hid]['pnl_pct']
        if pnl_pct > 100 or pnl_pct < -50:
            suspicious.append({
                'broker': h['broker'],
                'ticker': h['ticker'],
                'isin': h.get('isin', ''),
                'pnl_pct': pnl_pct,
                'live_price': live_prices[hid]['live_price'],
                'cost_basis': live_prices[hid]['cost_basis'],
                'live_value': live_prices[hid]['live_value']
            })

suspicious.sort(key=lambda x: abs(x['pnl_pct']), reverse=True)

print(f"{'Broker':<12} | {'Ticker':<10} | {'ISIN':<15} | {'P/L %':>8} | {'Price':>10} | Problema")
print("-" * 85)

for s in suspicious[:15]:
    # Identify problem type
    if s['pnl_pct'] > 200:
        problem = "Wrong ticker mapping?"
    elif s['pnl_pct'] > 100:
        problem = "Check price source"
    else:
        problem = "Normal loss?"
    
    print(f"{s['broker']:<12} | {s['ticker']:<10} | {s['isin']:<15} | {s['pnl_pct']:>+7.0f}% | {s['live_price']:>9.2f} | {problem}")

print()
print("=" * 75)
print("RIEPILOGO PROBLEMI")
print("=" * 75)

problems = []
for broker, app_val in app_values.items():
    dash_val = by_broker.get(broker, 0)
    diff = dash_val - app_val
    pct = (diff / app_val * 100) if app_val else 0
    if abs(pct) >= 15:
        problems.append(f"- {broker}: Dashboard EUR {dash_val:,.0f} vs App EUR {app_val:,} ({pct:+.0f}%)")

if problems:
    print("Broker con discrepanze significative:")
    for p in problems:
        print(p)
else:
    print("Tutti i broker entro tolleranza!")
