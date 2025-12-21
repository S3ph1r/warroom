"""
Confronto dettagliato REVOLUT: Dashboard vs App
"""
import sys
sys.path.insert(0, '.')
from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings, clear_cache

# User provided app values
APP_VALUES = {
    'GOOGL': 524,
    'BIDU': 317,
    'BP': 145,
    'XAU': 700,
    'XAG': 190,
    # Crypto totale ~27
    'POL': 10,    # Estimated
    'DOT': 8,
    'SOL': 5,
    '1INCH': 2,
    'AVAX': 2,
    'USD_CASH': 3,
}

print('Loading holdings and fetching live prices...')
holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

revolut = [h for h in holdings if h['broker'] == 'REVOLUT']

print()
print('=' * 95)
print('CONFRONTO DETTAGLIATO REVOLUT: DASHBOARD vs APP')
print('=' * 95)
print(f"{'Ticker':<12} | {'Type':<10} | {'Qty':>10} | {'App':>8} | {'Dashboard':>10} | {'Diff':>8} | Source")
print('-' * 95)

total_app = 0
total_dash = 0

for h in sorted(revolut, key=lambda x: -x['current_value']):
    ticker = h['ticker']
    hid = h['id']
    asset_type = h['asset_type']
    qty = h['quantity']
    app_val = APP_VALUES.get(ticker, 0)
    total_app += app_val
    
    if hid in live_data:
        ld = live_data[hid]
        dash_val = ld['live_value']
        source = ld['source']
    else:
        dash_val = float(h['current_value'])
        source = 'DB'
    
    total_dash += dash_val
    diff = dash_val - app_val
    
    print(f"{ticker:<12} | {asset_type:<10} | {qty:>10.4f} | {app_val:>8} | {dash_val:>10.2f} | {diff:>+8.0f} | {source}")

print('-' * 95)
print(f"{'TOTAL':<12} | {'':<10} | {'':<10} | {total_app:>8} | {total_dash:>10.2f} | {total_dash - total_app:>+8.0f}")
print()
print(f"App Total (user): EUR 1,903 (approx)")
print(f"Dashboard shows:  EUR 1,464.18 (user says)")
print(f"Script calculates: EUR {total_dash:.2f}")
