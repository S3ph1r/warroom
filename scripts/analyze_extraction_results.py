import json
import pandas as pd
from pathlib import Path

# Paths
DATA_DIR = Path(r"d:\Download\Progetto WAR ROOM\warroom\data\extracted")
CSV_JSON = DATA_DIR / "Posizioni_19-dic-2025_17_49_12.csv.json"
PDF_TRA_JSON = DATA_DIR / "Trades_19807401_2024-11-26_2025-12-18.pdf.json"
PDF_TRA_SMALL_JSON = DATA_DIR / "Transactions_19807401_2024-11-26_2025-12-19.pdf.json"

def analyze_holdings(filepath):
    print(f"\nANALYSIS: HOLDINGS ({filepath.name})")
    print("="*60)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('data', [])
        df = pd.DataFrame(items)
        
        if df.empty:
            print("No items found.")
            return

        # 1. Total Count
        print(f"Total Items: {len(df)}")
        
        # 2. Currencies
        if 'currency' in df.columns:
            print("\nBreakdown by Currency:")
            print(df['currency'].value_counts().to_string())

        # 3. Missing Data Check
        print("\nMissing Values:")
        print(df.isnull().sum().to_string())
        
        # 4. Date Format Check
        if 'date' in df.columns:
            sample_date = df['date'].iloc[0]
            print(f"\nDate Format Sample: '{sample_date}' (Needs normalization? {'-' in sample_date and 'dic' in sample_date})")

        # 5. Financial Summary (Approx)
        # We have price and quantity. Let's try to sum value per currency.
        if 'price' in df.columns and 'quantity' in df.columns:
            df['est_value'] = df['price'] * df['quantity']
            print("\nEstimated Value per Currency:")
            print(df.groupby('currency')['est_value'].sum().map('{:,.2f}'.format).to_string())

    except Exception as e:
        print(f"Error analyzing holdings: {e}")

def analyze_transactions(filepath):
    print(f"\nANALYSIS: TRANSACTIONS ({filepath.name})")
    print("="*60)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        items = data.get('data', [])
        df = pd.DataFrame(items)
        
        if df.empty:
            print("No items found.")
            return

        # 1. Total Count & Date Range
        print(f"Total Transactions: {len(df)}")
        if 'date' in df.columns:
            print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
            # Check format
            sample_date = df['date'].iloc[0]
            print(f"Date Format Sample: '{sample_date}'")

        # 2. Operations Breakdown
        if 'type' in df.columns:
            print("\nBreakdown by Type:")
            print(df['type'].value_counts().to_string())

        # 3. Currency Breakdown
        if 'currency' in df.columns:
            print("\nBreakdown by Currency:")
            print(df['currency'].value_counts().to_string())
            
        # 4. Total Amount Sum (Cash Flow)
        if 'total_amount' in df.columns:
            print("\nNet Cash Flow per Currency (Sum of total_amount):")
            print(df.groupby('currency')['total_amount'].sum().map('{:,.2f}'.format).to_string())

    except Exception as e:
        print(f"Error analyzing transactions: {e}")

if __name__ == "__main__":
    analyze_holdings(CSV_JSON)
    if PDF_TRA_JSON.exists():
        analyze_transactions(PDF_TRA_JSON)
    else:
        print(f"File not found: {PDF_TRA_JSON}")
    
    if PDF_TRA_SMALL_JSON.exists():
        analyze_transactions(PDF_TRA_SMALL_JSON)
