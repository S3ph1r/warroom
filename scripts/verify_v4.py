"""
Verify Dashboard Values vs App Values
"""
import sys
sys.path.insert(0, '.')

from services.portfolio_service import get_all_holdings
from services.price_service_v4 import get_live_values_for_holdings, clear_cache

print('Loading holdings and fetching live prices...')
holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

# App values provided by user
app_values = {
    'BG_SAXO': 19379,
    'TRADE_REPUBLIC': 2834,
    'SCALABLE': 4471,
    'IBKR': 418,
    'REVOLUT': 1966,
    'BINANCE': 3331,
}

# Calculate broker totals
broker_totals = {}
for h in holdings:
    broker = h['broker']
    hid = h['id']
    value = live_data[hid]['live_value'] if hid in live_data else h['current_value']
    broker_totals[broker] = broker_totals.get(broker, 0) + value

print()
print('=' * 75)
print('CONFRONTO DASHBOARD vs APP VALUES')
print('=' * 75)
print(f"{'Broker':<15} | {'Dashboard':>12} | {'App':>10} | {'Diff':>12} | Status")
print('-' * 75)

for broker, app_val in app_values.items():
    dash_val = broker_totals.get(broker, 0)
    diff = dash_val - app_val
    pct = (diff / app_val * 100) if app_val else 0
    
    if abs(pct) < 5:
        status = 'OK'
    elif abs(pct) < 15:
        status = 'CLOSE'
    else:
        status = 'MISMATCH'
    
    print(f"{broker:<15} | EUR {dash_val:>8,.0f} | {app_val:>9,} | {diff:>+7,.0f} ({pct:>+5.1f}%) | {status}")

print('-' * 75)
total_dash = sum(broker_totals.values())
total_app = sum(app_values.values())
total_diff = total_dash - total_app
print(f"{'TOTAL':<15} | EUR {total_dash:>8,.0f} | {total_app:>9,} | {total_diff:>+7,.0f}")

# Show fallback usage
print()
print('=' * 75)
print('PRICE SOURCES')
print('=' * 75)
sources = {}
for h in holdings:
    hid = h['id']
    if hid in live_data:
        src = live_data[hid]['source']
        sources[src] = sources.get(src, 0) + 1

for src, count in sorted(sources.items(), key=lambda x: -x[1]):
    print(f"  {src}: {count} holdings")
