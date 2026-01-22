import yfinance as yf
from decimal import Decimal

def debug_stock(symbol):
    print(f"Checking {symbol}...")
    stock = yf.Ticker(symbol)
    hist = stock.history(period="5d")
    print(f"History rows: {len(hist)}")
    if not hist.empty:
        print(hist[['Close']])
        current = Decimal(str(hist['Close'].iloc[-1]))
        prev = Decimal('0')
        if len(hist) >= 2:
            prev = Decimal(str(hist['Close'].iloc[-2]))
            print(f"Prev found in hist: {prev}")
        
        info_prev = stock.info.get('regularMarketPreviousClose') or stock.info.get('previousClose')
        print(f"Stock.info prev: {info_prev}")
        
        target_prev = prev if prev > 0 else (Decimal(str(info_prev)) if info_prev else None)
        if target_prev:
            change = float((current - target_prev) / target_prev * 100)
            print(f"Calculated Change: {change:.4f}%")
        else:
            print("No prev close found!")
    else:
        print("History EMPTY!")
    print("-" * 30)

if __name__ == "__main__":
    debug_stock("AAPL")
    debug_stock("CIBR.MI")
    debug_stock("BTC-USD")
