import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding
from sqlalchemy import select
import yfinance as yf

def check_tickers():
    db = SessionLocal()
    holdings = db.execute(select(Holding.ticker, Holding.broker, Holding.quantity, Holding.current_value)).all()
    print(f"Total Holdings: {len(holdings)}")
    unique_tickers = set()
    
    print("\n--- SAMPLE HOLDINGS ---")
    for h in holdings[:10]:
         print(f"[{h.broker}] {h.ticker} (Qty: {h.quantity}, Val: {h.current_value})")

    for h in holdings:
        unique_tickers.add(h.ticker)
    
    print(f"\nUnique Tickers Count: {len(unique_tickers)}")
    print("Unique Tickers List:", list(unique_tickers)[:20], "...")
    
    print("\n--- TESTING YFINANCE (BENCHMARKS) ---")
    benchmarks = ["^GSPC", "^NDX", "URTH"]
    for b in benchmarks:
        try:
             d = yf.Ticker(b).history(period="5d")
             if not d.empty:
                 print(f"✅ {b}: OK ({len(d)} rows)")
             else:
                 print(f"❌ {b}: EMPTY")
        except Exception as e:
             print(f"❌ {b}: ERROR {e}")
             
    print("\n--- TESTING YFINANCE (SAMPLE ASSETS) ---")
    # Test 3 random assets
    test_assets = list(unique_tickers)[:3]
    for t in test_assets:
        try:
             # Normalize (naive)
             search = t
             if not t.endswith("-USD"): # simplistic
                  pass 
             
             d = yf.Ticker(search).history(period="5d")
             status = "OK" if not d.empty else "EMPTY"
             print(f"Testing '{search}': {status}")
        except:
             print(f"Testing '{search}': ERROR")

    db.close()

if __name__ == "__main__":
    check_tickers()
