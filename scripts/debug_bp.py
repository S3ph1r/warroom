"""
Debug BP price differences between sources
"""
import yfinance as yf

# Test different BP tickers
tickers = ['BP.L', 'BP', 'BP.PA']

for t in tickers:
    try:
        s = yf.Ticker(t)
        h = s.history(period='1d')
        if not h.empty:
            price = h['Close'].iloc[-1]
            currency = s.info.get('currency', '?')
            
            # Calculate 5 shares value in EUR
            if currency == 'GBp':
                price_gbp = price / 100
                value_eur = 5 * price_gbp * 1.18
            elif currency == 'USD':
                value_eur = 5 * price * 0.853
            elif currency == 'EUR':
                value_eur = 5 * price
            else:
                value_eur = 5 * price
            
            print(f"{t:10} | Price: {price:>8.2f} {currency:5} | 5 shares = EUR {value_eur:>8.2f}")
    except Exception as e:
        print(f"{t:10} | Error: {e}")

print()
print("User says BP on Revolut = EUR 145 for 5 shares")
print("So price per share = EUR 29")
print("BP NYSE (USD) at ~$34 * 0.853 = EUR 29 matches!")
