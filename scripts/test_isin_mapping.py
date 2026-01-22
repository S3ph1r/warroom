"""
Test ISIN to Yahoo ticker mapping
"""
import sys
sys.path.insert(0, '.')

import importlib
import services.price_service_v5 as ps
importlib.reload(ps)

tests = [
    ('SWDA', 'IE00B4L5Y983', 'iShares World'),
    ('NUCL', 'IE000M7V94E1', 'VanEck Uranium'),
    ('XAIX', 'IE00BGV5VN51', 'Xtrackers AI'),
    ('CIBR', None, 'Cyber Security'),
    ('AMZN', 'US0231351067', 'Amazon'),
    ('AMP', 'IT0004056880', 'Amplifon'),
    ('BIDU', 'US0567521085', 'Baidu'),
]

print('ISIN to Yahoo ticker mapping:')
print('=' * 70)
for ticker, isin, name in tests:
    result = ps.isin_to_yahoo_ticker(isin, ticker)
    isin_str = isin if isin else 'None'
    print(f"{ticker:8} + {isin_str:15} -> {result:15} | {name}")
