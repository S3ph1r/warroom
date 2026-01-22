
import pandas as pd
import json
import os
import sys

# MAPPING CONFIGURATION (Italian BG SAXO CSV -> English JSON Keys)
COLUMN_MAP = {
    "Strumento": "name",
    "Quantità": "quantity",
    "Prezzo di apertura": "purchase_price",
    "Prz. corrente": "current_price", 
    "Valuta": "currency",
    "ISIN": "isin",
    "Ticker": "ticker",
    "Tipo attività": "asset_type"
}

def clean_and_convert_csv(file_path):
    print(f"🕵️‍♂️ Analyzing CSV: {file_path}")
    
    # 1. LOAD: Read CSV standard (Header is usually line 1 for BG SAXO)
    # We use on_bad_lines='skip' just in case, but structure seems clean.
    try:
        # Force encoding to utf-8-sig to handle BOM if present
        # Force separator to comma (it looks like comma separate)
        # Force index_col=False to prevent first column being used as index
        df = pd.read_csv(file_path, on_bad_lines='skip', encoding='utf-8-sig', sep=',', quotechar='"', index_col=False)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print("   🔍 DEBUG COLUMNS:", df.columns.tolist()[:5])
    if not df.empty:
        print("   🔍 DEBUG FIRST ROW:", df.iloc[0].tolist()[:5])


    print(f"   Raw Rows: {len(df)}")
    
    # Check if we have the critical ISIN column
    if "ISIN" not in df.columns:
        print("❌ Critical Column 'ISIN' not found! Headers detected:", df.columns.tolist())
        return

    # 2. FILTER: The Magic Trick 🪄
    # Valid assets have an ISIN. Summary rows (like "Azioni (48)") DO NOT.
    # So we simply drop rows where ISIN is NaN or Empty.
    df_clean = df.dropna(subset=['ISIN'])
    df_clean = df_clean[df_clean['ISIN'].str.strip() != '']
    
    print(f"   Valid Asset Rows (ISIN present): {len(df_clean)}")

    # 3. NORMALIZE: Rename columns to our internal schema
    df_norm = df_clean.rename(columns=COLUMN_MAP)
    
    # Select only relevant columns (if they exist)
    target_cols = [c for c in COLUMN_MAP.values() if c in df_norm.columns]
    df_final = df_norm[target_cols].copy()
    
    # 4. DATA TYPING: Ensure numbers are numbers, strings are strings
    if 'quantity' in df_final.columns:
        # Remove thousands separators if any (Italian fmt: 1.000,00 -> 1000.00) usually BG Saxo CSV is '45' or '4.55' depending on locale.
        # From sample: '45', '2.891..' -> Looks like dot decimal.
        # But wait, looking at file sample: "4,66" in Bid/Ask but "2.891" in Price.
        # Line 3 Quantity: "45". Line 53 Quantity: "5.659" (Wait, 5659 share or 5.659? Ah, line 53 is PRICE). 
        # Quantity line 53 is "100".
        pass 

    # 5. ASSET TYPE INFERENCE (If missing or needs mapping)
    # The CSV has "Tipo attività" -> "Azione", "Exchange Traded Fund (ETF)"
    if 'asset_type' in df_final.columns:
        type_map = {
            'Azione': 'STOCK',
            'Exchange Traded Fund (ETF)': 'ETF',
            'Obbligazione': 'BOND'
        }
        df_final['asset_type'] = df_final['asset_type'].map(type_map).fillna('STOCK')

    # Convert to JSON List
    records = df_final.to_dict(orient='records')
    
    # Output path
    base_name = os.path.basename(file_path)
    output_path = os.path.join(os.path.dirname(file_path), base_name + ".smart.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"holdings": records}, f, indent=2, default=str)
        
    print(f"✅ SUCCESS! Extracted {len(records)} holdings.")
    print(f"   Saved to: {output_path}")
    print("   Sample:", records[0])

if __name__ == "__main__":
    # Test on the file we know exists
    target = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv"
    clean_and_convert_csv(target)
