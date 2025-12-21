"""
Compare each BG_SAXO asset with user-provided app values
Using price_service_v5 with OpenFIGI
"""
import sys
sys.path.insert(0, '.')
from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings, clear_cache

# User provided app values (Market Value EUR)
APP_VALUES = {
    # Stocks
    'AHLA': 257,      # Alibaba (BG Saxo ticker)
    'GOOGL': 524,
    'AMZN': 776,
    'AMP': 96,
    'ANET': 448,
    'ARM': 97,
    'ASTS': 131,
    'BIDU': 531,
    'BYDDY': 204,
    'CDTG': 187,
    'CVX': 126,
    'CRSP': 238,
    'QBTS': 342,
    'DT': 113,
    'ETL': 74,
    'RACE': 323,
    'INTC': 946,
    'KULR': 219,
    'LDO': 98,
    'META': 563,
    'NOKIA': 437,
    'NOVOB': 331,
    'NVDA': 308,
    'OKLO': 71,
    'ORCL': 493,
    'PLTR': 660,
    'PANW': 159,
    'PYPL': 153,
    'PDD': 188,
    'QRVO': 146,
    'QCOM': 299,
    'QUBT': 93,
    'QS': 195,
    'XBOT': 67,       # Realbotix (BG Saxo ticker is XBOT)
    'NOW': 133,
    'SLDP': 4,
    'SAI': 104,
    'TER': 168,
    'TM': 374,
    'TSM': 247,
    'UAMY': 205,
    'VKTX': 150,
    'VNET': 75,
    'VOYG': 691,
    'WMT': 487,
    'WBD': 347,
    'XPEV': 255,
    '02050': 381,     # Zhejiang Sanhua
    
    # ETFs
    'CIBR': 390,
    'FLXI': 193,
    'SWDA': 1110,
    'ICGA': 530,
    'KSTR': 173,
    'NUCL': 944,      # BG Saxo uses NUCL not NUKL
    'XAIX': 1681,
    
    # Cash
    'CASH': 845,
}

print("Loading holdings and fetching live prices...")
holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

bg_saxo = [h for h in holdings if h['broker'] == 'BG_SAXO']

print()
print("=" * 100)
print("CONFRONTO DETTAGLIATO BG_SAXO - OGNI ASSET")
print("=" * 100)
print(f"{'Ticker':<10} | {'App':>8} | {'Dashboard':>10} | {'Diff':>8} | {'Diff%':>7} | Source")
print("-" * 100)

total_app = 0
total_dash = 0
big_diffs = []

for h in sorted(bg_saxo, key=lambda x: -x['current_value']):
    ticker = h['ticker']
    hid = h['id']
    
    app_val = APP_VALUES.get(ticker, 0)
    total_app += app_val
    
    if hid in live_data:
        ld = live_data[hid]
        dash_val = ld['live_value']
        source = ld['source']
    else:
        dash_val = float(h['current_value'])
        source = "DB"
    
    total_dash += dash_val
    
    diff = dash_val - app_val
    diff_pct = (diff / app_val * 100) if app_val else 0
    
    # Flag if difference > 5%
    flag = "X" if abs(diff_pct) > 5 else "OK"
    
    print(f"{ticker:<10} | {app_val:>8} | {dash_val:>10.0f} | {diff:>+8.0f} | {diff_pct:>+6.1f}% | {flag} {source}")
    
    if abs(diff_pct) > 5 and abs(diff) > 10:
        big_diffs.append({
            'ticker': ticker,
            'app': app_val,
            'dash': dash_val,
            'diff': diff,
            'pct': diff_pct,
            'source': source
        })

print("-" * 100)
print(f"{'TOTAL':<10} | {total_app:>8} | {total_dash:>10.0f} | {total_dash - total_app:>+8.0f} | {(total_dash - total_app) / total_app * 100:>+6.1f}%")

print()
print("=" * 100)
print("ASSET CON DIFFERENZA > 5%")
print("=" * 100)

if big_diffs:
    big_diffs.sort(key=lambda x: -abs(x['diff']))
    for d in big_diffs:
        print(f"  {d['ticker']:<10} | App: {d['app']:>6} | Dash: {d['dash']:>6.0f} | Diff: {d['diff']:>+6.0f} ({d['pct']:>+5.1f}%) | {d['source']}")
else:
    print("  Nessun asset con differenza > 5%!")
