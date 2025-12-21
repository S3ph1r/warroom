"""
Confronto dettagliato BG_SAXO: Dashboard vs App
Mostra ogni asset e la differenza per trovare i ~300 EUR mancanti
"""
import sys
sys.path.insert(0, '.')
from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings, clear_cache

# User provided app values (Market Value EUR)
APP_VALUES = {
    # Stocks (48)
    'AHLA': 257, 'GOOGL': 524, 'AMZN': 776, 'AMP': 96, 'ANET': 448,
    'ARM': 97, 'ASTS': 131, 'BIDU': 531, 'BYDDY': 204, 'CDTG': 187,
    'CVX': 126, 'CRSP': 238, 'QBTS': 342, 'DT': 113, 'ETL': 74,
    'RACE': 323, 'INTC': 946, 'KULR': 219, 'LDO': 98, 'META': 563,
    'NOKIA': 437, 'NOVOB': 331, 'NVDA': 308, 'OKLO': 71, 'ORCL': 493,
    'PLTR': 660, 'PANW': 159, 'PYPL': 153, 'PDD': 188, 'QRVO': 146,
    'QCOM': 299, 'QUBT': 93, 'QS': 195, 'XBOT': 67, 'NOW': 133,
    'SLDP': 4, 'SAI': 104, 'TER': 168, 'TM': 374, 'TSM': 247,
    'UAMY': 205, 'VKTX': 150, 'VNET': 75, 'VOYG': 691, 'WMT': 487,
    'WBD': 347, 'XPEV': 255, '02050': 381,
    # ETFs (7)
    'CIBR': 390, 'FLXI': 193, 'SWDA': 1110, 'ICGA': 530, 'KSTR': 173,
    'NUCL': 944, 'XAIX': 1681,
    # Cash
    'CASH': 845,
}

print('Loading holdings and fetching live prices...')
holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

bg_saxo = [h for h in holdings if h['broker'] == 'BG_SAXO']

# Sort by value descending
items = []
for h in bg_saxo:
    ticker = h['ticker']
    hid = h['id']
    app_val = APP_VALUES.get(ticker, 0)
    
    if hid in live_data:
        ld = live_data[hid]
        dash_val = ld['live_value']
        source = ld['source']
    else:
        dash_val = float(h['current_value'])
        source = 'DB'
    
    diff = dash_val - app_val
    items.append((ticker, app_val, dash_val, diff, source))

items.sort(key=lambda x: -x[1])  # Sort by app value desc

print()
print('=' * 95)
print('CONFRONTO DETTAGLIATO BG_SAXO: DASHBOARD vs APP')
print('=' * 95)
print(f"{'Ticker':<10} | {'App':>8} | {'Dashboard':>10} | {'Diff':>8} | {'%':>6} | Source")
print('-' * 95)

total_app = 0
total_dash = 0

for ticker, app_val, dash_val, diff, source in items:
    total_app += app_val
    total_dash += dash_val
    
    pct = (diff / app_val * 100) if app_val else 0
    flag = '' if abs(pct) < 5 else '*'
    
    print(f"{ticker:<10} | {app_val:>8} | {dash_val:>10.0f} | {diff:>+8.0f} | {pct:>+5.1f}% | {flag}{source}")

print('-' * 95)
print(f"{'TOTAL':<10} | {total_app:>8} | {total_dash:>10.0f} | {total_dash - total_app:>+8.0f} | {(total_dash-total_app)/total_app*100:>+5.1f}%")
print()

# Show biggest differences
print('TOP 10 DIFFERENZE (per valore assoluto):')
print('-' * 60)
items.sort(key=lambda x: -abs(x[3]))
for i, (ticker, app_val, dash_val, diff, source) in enumerate(items[:10]):
    pct = (diff / app_val * 100) if app_val else 0
    print(f"  {i+1}. {ticker:<10} | Diff: {diff:>+6.0f} EUR ({pct:>+5.1f}%) | {source}")
