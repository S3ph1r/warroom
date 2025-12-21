"""
Analyze P/L per asset - sorted by losses
"""
import sys
sys.path.insert(0, '.')
from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings, clear_cache

holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

results = []
for h in holdings:
    hid = h['id']
    ticker = h['ticker']
    broker = h['broker']
    qty = h['quantity']
    purchase_price = h.get('purchase_price', 0) or 0
    
    if hid in live_data:
        ld = live_data[hid]
        pnl = ld['pnl']
        live_val = ld['live_value']
        cost = ld['cost_basis']
    else:
        pnl = 0
        live_val = h['current_value']
        cost = qty * purchase_price
    
    results.append({
        'ticker': ticker,
        'broker': broker,
        'pnl': pnl,
        'live_val': live_val,
        'cost': cost,
        'purchase_price': purchase_price
    })

# Sort by P/L (losses first)
results.sort(key=lambda x: x['pnl'])

print('TOP LOSSES (ordinato per P/L crescente):')
print('='*95)
print(f"{'Ticker':<10} | {'Broker':<12} | {'P/L':>10} | {'Val Live':>10} | {'Costo':>10} | {'Prezzo Acq':>10}")
print('-'*95)

for r in results[:30]:  # Top 30 losses
    print(f"{r['ticker']:<10} | {r['broker']:<12} | {r['pnl']:>+10.0f} | {r['live_val']:>10.0f} | {r['cost']:>10.0f} | {r['purchase_price']:>10.2f}")

print('-'*95)
total_all = sum([r['pnl'] for r in results])
print(f"Total P/L (all assets): EUR {total_all:+,.0f}")
