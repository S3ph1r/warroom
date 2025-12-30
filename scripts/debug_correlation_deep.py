import sys
import os
from pathlib import Path
import pandas as pd
import yfinance as yf

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from services.analytics_service import normalize_ticker
from services.portfolio_service import get_all_holdings

def debug_corr():
    print("--- DEBUG CORRELATION ---")
    holdings = get_all_holdings()
    print(f"Total Holdings: {len(holdings)}")
    
    valid_holdings = []
    for h in holdings:
        val = h.get('current_value') or 0
        if val <= 0: continue
        
        raw_ticker = h.get('ticker')
        atype = h.get('asset_type')
        norm = normalize_ticker(raw_ticker, atype)
        
        print(f"Holding: {raw_ticker} ({atype}) Val={val} -> Norm={norm}")
        
        if norm:
            h['yf_ticker'] = norm
            valid_holdings.append(h)
            
    print(f"Valid Holdings for Matrix: {len(valid_holdings)}")
    
    if not valid_holdings:
        print("❌ No valid holdings found!")
        return

    # Sort and take top 5
    valid_holdings.sort(key=lambda x: float(x.get('current_value', 0)), reverse=True)
    top = valid_holdings[:5]
    tickers = [x['yf_ticker'] for x in top]
    print(f"Top 5 Tickers: {tickers}")
    
    print("\n--- ATTEMPTING YFINANCE DOWNLOAD ---")
    try:
        data = yf.download(
            tickers,
            period="5d",
            progress=True,
            auto_adjust=True,
            threads=False
        )
        print("Download Result Type:", type(data))
        print(data.head())
        
        if data.empty:
            print("❌ Data is EMPTY")
        else:
            print("✅ Data OK")
            # Check columns
            if isinstance(data.columns, pd.MultiIndex):
                print("Columns (MultiIndex):", data.columns)
                if 'Close' in data.columns:
                     closes = data['Close']
                     print("Closes Shape:", closes.shape)
            else:
                 print("Columns:", data.columns)

    except Exception as e:
        print(f"❌ YF Error: {e}")

if __name__ == "__main__":
    debug_corr()
