"""Parse Revolut Excel files (CSV-in-cell format)"""
import pandas as pd
from pathlib import Path
from io import StringIO

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut")

files = {
    "TRADING": "trading-account-statement_2019-12-28_2025-12-31_it-it_28f506.xlsx",
    "CRYPTO": "crypto-account-statement_2022-07-04_2025-12-31_it-it_87d838.xlsx",
    "ACCOUNT_MAIN": "account-statement_2017-12-26_2025-12-31_it-it_18a170.xlsx",
    "ACCOUNT_COMMODITIES": "account-statement_2022-07-26_2025-12-31_it-it_43269b.xlsx",
}

for name, fname in files.items():
    fpath = INBOX / fname
    print(f"\n{'='*70}")
    print(f"📂 {name} - {fname}")
    print('='*70)
    
    # Read as single-column Excel
    df_raw = pd.read_excel(fpath, engine='calamine', header=None)
    
    # Join all cells and parse as CSV
    csv_text = '\n'.join(df_raw[0].astype(str).tolist())
    df = pd.read_csv(StringIO(csv_text))
    
    print(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    print(f"Columns: {list(df.columns)}")
    
    # Show sample
    if len(df) > 0:
        print(f"\nSample row 0:")
        for col, val in df.iloc[0].items():
            print(f"  {col}: {val}")
    
    # Check for unique tickers/assets
    if 'Ticker' in df.columns:
        print(f"\nUnique Tickers: {df['Ticker'].nunique()}")
        print(f"Sample: {df['Ticker'].dropna().unique()[:5].tolist()}")
    elif 'Prodotto' in df.columns:
        print(f"\nUnique Products: {df['Prodotto'].nunique()}")
        print(f"Sample: {df['Prodotto'].dropna().unique()[:5].tolist()}")
