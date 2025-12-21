"""
Analyze BG_SAXO holdings to find discrepancy source
"""
import sys
sys.path.insert(0, '.')
from services.portfolio_service import get_all_holdings
from services.price_service_v4 import get_live_values_for_holdings, clear_cache

holdings = get_all_holdings()
clear_cache()
live_data = get_live_values_for_holdings(holdings)

print('BG_SAXO Holdings (top 20 by value):')
print('=' * 95)

bg_saxo = [h for h in holdings if h['broker'] == 'BG_SAXO']

items = []
for h in bg_saxo:
    hid = h['id']
    ld = live_data.get(hid, {})
    live_val = ld.get('live_value', h['current_value'])
    pnl_pct = ld.get('pnl_pct', 0)
    source = ld.get('source', 'N/A')
    items.append({
        'ticker': h['ticker'],
        'value': live_val,
        'pnl_pct': pnl_pct,
        'source': source,
        'qty': h.get('quantity', 0),
        'purch': h.get('purchase_price') or 0
    })

items.sort(key=lambda x: -x['value'])

for i in items[:20]:
    print(f"{i['ticker']:<12} | {i['value']:>10,.2f} | {i['pnl_pct']:>+7.1f}% | {i['source']:<20} | {i['qty']:>8.2f}")

print('-' * 95)
print(f"Total BG_SAXO: EUR {sum(i['value'] for i in items):,.2f}")
print(f"App value:     EUR 19,379")
print(f"Difference:    EUR {sum(i['value'] for i in items) - 19379:,.2f}")

# Find suspicious items (high P/L)
print()
print('Holdings con P/L sospetti (>50% o <-50%):')
suspicious = [i for i in items if abs(i['pnl_pct']) > 50]
for i in sorted(suspicious, key=lambda x: -abs(x['pnl_pct'])):
    print(f"  {i['ticker']:<12} P/L: {i['pnl_pct']:>+7.1f}% | Value: {i['value']:>8.2f} | Source: {i['source']}")
