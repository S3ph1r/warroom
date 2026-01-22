"""
Test EU ETF tickers on Yahoo Finance
"""
import yfinance as yf

# Test SWDA on different exchanges
etfs_to_test = [
    ('SWDA.MI', 'SWDA Italy'),
    ('SWDA.L', 'SWDA London'),
    ('SWDA.DE', 'SWDA Germany'),
    ('IWDA.AS', 'IWDA Amsterdam'),
    ('XAIX.DE', 'Xtrackers AI Germany'),
    ('CIBR.L', 'CIBR London'),
    ('NUKL.DE', 'VanEck Uranium'),
]

print("Testing EU ETFs on Yahoo Finance:")
print("=" * 60)

for ticker, name in etfs_to_test:
    try:
        s = yf.Ticker(ticker)
        h = s.history(period='1d')
        if not h.empty:
            price = h['Close'].iloc[-1]
            currency = s.info.get('currency', '?')
            print(f"{ticker:12} | {name:25} | {price:>8.2f} {currency}")
        else:
            print(f"{ticker:12} | {name:25} | NO DATA")
    except Exception as e:
        print(f"{ticker:12} | {name:25} | ERROR: {e}")
