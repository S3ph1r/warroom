import yfinance as yf

def test_nvda():
    print("Testing NVDA fetch...")
    t = yf.Ticker("NVDA")
    hist = t.history(period="5d")
    print(hist)
    print("Empty?", hist.empty)
    
    if not hist.empty:
        print("Last Close:", hist['Close'].iloc[-1])

if __name__ == "__main__":
    test_nvda()
