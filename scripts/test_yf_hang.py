
import yfinance as yf
from datetime import datetime, timedelta
import sys

print("Testing yfinance download...")
try:

    tickers = ["^GSPC", "^NDX", "URTH"]
    for t in tickers:
        print(f"Downloading {t}...")
        try:
            data = yf.download(t, period="1mo", progress=True, auto_adjust=True)
            print(f"Success {t}: {data.shape}")
        except Exception as e:
            print(f"Failed {t}: {e}")
except Exception as e:
    print(f"Global Error: {e}")

