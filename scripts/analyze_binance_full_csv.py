"""Analyze New Binance CSV and Excel"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance")
CSV_PATH = BASE_DIR / "extracted" / "ea91c32a-e883-11f0-932a-0e89d0e894f3-1.csv"
XLSX_PATH = BASE_DIR / "Binance-Report-storico-dei-depositi-2026-01-03.xlsx"

print(f"=== ANALYZING: {CSV_PATH.name} ===")
try:
    # Read first few lines to detect skip_rows or structure
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        print("First 5 lines:")
        for _ in range(5):
            print(f.readline().strip())
            
    # Attempt pandas load
    df = pd.read_csv(CSV_PATH)
    print(f"\nDataFrame Info:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nSample Data (First 3 rows):")
    print(df.head(3).to_string())
    
    # Check date range
    if 'User_Time' in df.columns:
        print(f"\nDate Range (User_Time): {df['User_Time'].min()} to {df['User_Time'].max()}")
    elif 'UTC_Time' in df.columns:
        print(f"\nDate Range (UTC_Time): {df['UTC_Time'].min()} to {df['UTC_Time'].max()}")
        
except Exception as e:
    print(f"❌ Error reading CSV: {e}")

print(f"\n\n=== ANALYZING: {XLSX_PATH.name} ===")
try:
    df_xlsx = pd.read_excel(XLSX_PATH)
    print(f"Rows: {len(df_xlsx)}")
    print(f"Columns: {list(df_xlsx.columns)}")
    print(df_xlsx.head(3).to_string())
except Exception as e:
    print(f"❌ Error reading XLSX: {e}")
