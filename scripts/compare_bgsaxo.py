"""
Compare BG_SAXO App Data vs DB Data
User provided real values from broker app
"""
import sys
sys.path.insert(0, '.')
from db.database import SessionLocal
from db.models import Holding
from decimal import Decimal

# User-provided data from BG_SAXO app
APP_DATA = {
    # Ticker: (Qty, Open Price, Current Price, Market Value EUR)
    # Stocks (48)
    'BABA': (2, 134.60, 128.60, 257),
    'GOOGL': (2, 301.93, 307.34, 524),
    'AMZN': (4, 219.51, 227.59, 776),
    'AMP': (7, 13.975, 13.645, 96),
    'ANET': (4, 148.85, 131.39, 448),
    'ARM': (1, 169.83, 114.20, 97),
    'ASTS': (2, 65.86, 76.68, 131),
    'BIDU': (5, 128.93, 124.60, 531),
    'BYDDY': (20, 13.12, 12.00, 204),
    'CDTG': (500, 0.5592, 0.4390, 187),
    'CVX': (1, 148.85, 147.64, 126),
    'CRSP': (5, 56.03, 55.97, 238),
    'QBTS': (15, 29.55, 26.74, 342),
    'DT': (3, 58.58, 44.30, 113),
    'ETL': (45, 2.891, 1.640, 74),
    'RACE': (1, 374.60, 322.80, 323),
    'INTC': (30, 27.92, 37.01, 946),
    'KULR': (80, 3.82, 3.21, 219),
    'LDO': (2, 43.27, 49.22, 98),
    'META': (1, 769.70, 660.30, 563),
    'NOKIA': (80, 4.550, 5.458, 437),
    'NOVOB': (8, 411.35, 310.00, 331),
    'NVDA': (2, 183.57, 181.00, 308),
    'OKLO': (1, 76.92, 83.49, 71),
    'ORCL': (3, 222.53, 193.07, 493),
    'PLTR': (4, 151.34, 193.75, 660),
    'PANW': (1, 186.23, 186.90, 159),
    'PYPL': (3, 89.53, 59.80, 153),
    'PDD': (2, 108.00, 110.09, 188),
    'QRVO': (2, 85.55, 85.63, 146),
    'QCOM': (2, 151.69, 175.30, 299),
    'QUBT': (10, 9.1548, 10.86, 93),
    'QS': (20, 4.93, 11.47, 195),
    'RBOT': (300, 0.435, 0.360, 67),
    'NOW': (1, 155.29, 155.68, 133),
    'SLDP': (1, 3.42, 4.71, 4),
    'SAI': (1300, 0.09, 0.08, 104),
    'TER': (1, 190.26, 197.02, 168),
    'TM': (2, 215.81, 219.50, 374),
    'TSM': (1, 295.00, 290.29, 247),
    'UAMY': (50, 5.9724, 4.82, 205),
    'VKTX': (5, 34.744, 35.22, 150),
    'VNET': (10, 10.37, 8.75, 75),
    'VOYG': (30, 24.811, 27.05, 691),
    'WMT': (5, 102.18, 114.37, 487),
    'WBD': (100, 2.648, 3.472, 347),
    'XPEV': (15, 21.03, 19.93, 255),
    # Zhejiang Sanhua - ticker?
    '02050': (100, 31.94, 34.80, 381),
    
    # ETFs (7)
    'CIBR': (10, 38.624, 39.035, 390),
    'FLXI': (5, 37.830, 38.510, 193),
    'SWDA': (10, 96.893, 110.950, 1110),
    'ICGA': (100, 5.659, 5.301, 530),
    'KSTR': (10, 16.968, 17.340, 173),
    'NUKL': (20, 51.467, 47.190, 944),
    'XAIX': (11, 135.17, 152.82, 1681),
    
    # Cash
    'CASH': (845.18, 1, 1, 845),
}

# Total from app
APP_TOTAL = 19379.80
APP_CASH = 845.18

session = SessionLocal()
db_holdings = session.query(Holding).filter(Holding.broker == 'BG_SAXO').all()

print('=' * 100)
print('CONFRONTO BG_SAXO: APP vs DB')
print('=' * 100)

# Create DB lookup
db_lookup = {}
for h in db_holdings:
    ticker = h.ticker
    db_lookup[ticker] = {
        'qty': float(h.quantity),
        'purch_price': float(h.purchase_price) if h.purchase_price else 0,
        'current_price': float(h.current_price) if h.current_price else 0,
        'current_value': float(h.current_value),
        'asset_type': h.asset_type
    }

print(f"\n{'Ticker':<10} | {'App Qty':>10} | {'DB Qty':>10} | {'App Val':>10} | {'DB Val':>10} | Status")
print('-' * 100)

discrepancies = []
matched = 0
total_app = 0
total_db = 0

for ticker, (app_qty, app_open, app_curr, app_val) in APP_DATA.items():
    total_app += app_val
    
    if ticker in db_lookup:
        db = db_lookup[ticker]
        db_val = db['current_value']
        total_db += db_val
        
        qty_match = abs(db['qty'] - app_qty) < 0.01
        val_diff = abs(db_val - app_val)
        val_match = val_diff < 50  # Allow €50 tolerance
        
        if qty_match and val_match:
            status = 'OK'
            matched += 1
        else:
            status = 'DIFF'
            discrepancies.append({
                'ticker': ticker,
                'app_qty': app_qty,
                'db_qty': db['qty'],
                'app_val': app_val,
                'db_val': db_val,
                'diff': db_val - app_val
            })
        
        print(f"{ticker:<10} | {app_qty:>10.2f} | {db['qty']:>10.2f} | {app_val:>10.0f} | {db_val:>10.0f} | {status}")
    else:
        print(f"{ticker:<10} | {app_qty:>10.2f} | {'MISSING':>10} | {app_val:>10.0f} | {'N/A':>10} | MISSING")
        discrepancies.append({
            'ticker': ticker,
            'app_qty': app_qty,
            'db_qty': 0,
            'app_val': app_val,
            'db_val': 0,
            'diff': -app_val
        })

# Check for DB entries not in app
print('\n' + '-' * 100)
print('Holdings in DB but NOT in App:')
for ticker, db in db_lookup.items():
    if ticker not in APP_DATA:
        print(f"  {ticker:<10} | Qty: {db['qty']:>10.2f} | Val: {db['current_value']:>10.0f}")
        total_db += db['current_value']

print('\n' + '=' * 100)
print('RIEPILOGO')
print('=' * 100)
print(f"App Total:  EUR {APP_TOTAL:>12,.2f}")
print(f"DB Total:   EUR {sum(h.current_value for h in db_holdings):>12,.2f}")
print(f"Matched:    {matched}/{len(APP_DATA)} holdings")
print(f"Discrepancies: {len(discrepancies)}")

if discrepancies:
    print('\n' + '-' * 100)
    print('DISCREPANZE PRINCIPALI (ordinate per differenza):')
    discrepancies.sort(key=lambda x: abs(x['diff']), reverse=True)
    for d in discrepancies[:10]:
        print(f"  {d['ticker']:<10} | App: {d['app_val']:>8.0f} | DB: {d['db_val']:>8.0f} | Diff: {d['diff']:>+8.0f}")

session.close()
