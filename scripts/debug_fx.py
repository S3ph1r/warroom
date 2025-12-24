
import yfinance as yf
import sys

def test_fx():
    print("Testing EURUSD=X...")
    ticker = yf.Ticker("EURUSD=X")
    try:
        hist = ticker.history(period="1d")
        print(f"History: {hist}")
        if not hist.empty:
            print(f"Close: {hist['Close'].iloc[-1]}")
        else:
            print("Empty history.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fx()
