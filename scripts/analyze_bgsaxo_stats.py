import json
import pandas as pd
from pathlib import Path

# Paths
DATA_DIR = Path(r"d:\Download\Progetto WAR ROOM\warroom\data\extracted\bgsaxo")
CLEAN_DIR = Path(r"d:\Download\Progetto WAR ROOM\warroom\data\clean")

def analyze_bgsaxo():
    print("🔎 ANALISI COMPARATIVA: BG SAXO")
    print("="*60)
    
    # 1. HOLDINGS (CSV Extracted)
    holdings = []
    for f in DATA_DIR.glob("*Posizioni*.json"):
         with open(f, 'r', encoding='utf-8') as j:
             data = json.load(j)
             holdings.extend(data.get('data', []))
    
    df_h = pd.DataFrame(holdings)
    if not df_h.empty:
        # Normalize quantity handling
        df_h['qty'] = pd.to_numeric(df_h['quantity'], errors='coerce').fillna(0)
        
        print(f"\n📌 HOLDINGS (Source of Truth): {len(df_h)} Assets")
        print(df_h[['ticker', 'qty', 'currency']].head().to_string())
        print(f"Total Portfolio Qty: {df_h['qty'].sum():.2f}")
    
    # 2. TRANSACTIONS (PDF Extracted)
    txs = []
    for f in DATA_DIR.glob("*Trade*.json"): # Matches Trades...pdf.json and Transactions...pdf.json
         with open(f, 'r', encoding='utf-8') as j:
             data = json.load(j)
             items = data.get('data', [])
             txs.extend(items)
             
    df_t = pd.DataFrame(txs)
    if not df_t.empty:
         # Normalize Qty
         def parse_qty(x):
             try: return float(x)
             except: return 0.0
         
         df_t['qty'] = df_t['quantity'].apply(parse_qty)
         
         # Logic: Sell is usually negative in our standard, but raw might be positive with type=SELL
         # Let's see raw Sum
         print(f"\n📜 TRANSACTIONS (Raw Extracted): {len(df_t)} Records")
         print(df_t[['date', 'type', 'ticker', 'qty']].head().to_string())
         print(f"Total Raw Qty Sum: {df_t['qty'].sum():.2f}")

    # 3. CLEAN RECONCILED (Final History)
    clean_file = CLEAN_DIR / "bgsaxo_history.json"
    if clean_file.exists():
        with open(clean_file, 'r', encoding='utf-8') as f:
            clean_data = json.load(f)
        
        df_c = pd.DataFrame(clean_data)
        print(f"\n✅ CLEAN HISTORY (Reconciled): {len(df_c)} Records")
        
        # Breakdown by Type
        print("\nBreakdown by Type:")
        print(df_c['type'].value_counts().to_string())
        
        # Verify specific ticker Example: NVDA
        nvda = df_c[df_c['ticker'].str.contains('NVDA', case=False, na=False)]
        if not nvda.empty:
            print("\nExample NVDA History:")
            print(nvda[['date', 'type', 'ticker', 'quantity']].to_string())
            print(f"NVDA Final Sum: {nvda['quantity'].sum()}")

if __name__ == "__main__":
    analyze_bgsaxo()
