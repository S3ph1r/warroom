
import pandas as pd
import json
import os
import sys

def load_csv_with_rules(csv_path, rules_path):
    print(f"🤖 Universal Smart Loader: {csv_path}")
    print(f"   📜 Using Rules: {rules_path}")
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)
        
    # Rules Schema: {"header_row": int, "sep": str, "mapping": dict, "filter_column": str}
    
    try:
        # 1. LOAD using Rules
        df = pd.read_csv(
            csv_path,
            header=rules.get('header_row', 0),
            sep=rules.get('sep', ','),
            on_bad_lines='skip',
            encoding='utf-8-sig',
            index_col=False # Always false to match our manual fix
        )
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    print(f"   Raw Rows: {len(df)}")
    
    # 2. FILTER
    filter_col = rules.get('filter_column')
    if filter_col:
        if filter_col not in df.columns:
            print(f"⚠️ Warning: Filter column '{filter_col}' not found. Skipping filter.")
            print(f"   Available columns: {df.columns.tolist()[:5]}...")
        else:
            df = df.dropna(subset=[filter_col])
            # Try to filter empty strings too
            # df = df[df[filter_col].astype(str).str.strip() != '']
    
    # 3. MAPPING
    mapping = rules.get('mapping', {})
    # Invert mapping? No, Config should be "Original" -> "Standard"
    
    # Rename
    df = df.rename(columns=mapping)
    
    # Keep only standard columns
    standard_cols = list(mapping.values())
    # Add any extra columns we might want? No, keep it strict.
    
    final_cols = [c for c in df.columns if c in standard_cols]
    df_final = df[final_cols].copy()
    
    # 4. STATIC TYPING ENFORCEMENT
    # If standard columns exist, enforce types
    if 'quantity' in df_final.columns:
        # Handle comma/dot mess?
        pass # Let output be string-ish or float, JSON consumer handles detailed conversion
        
    # EXPORT
    output_path = csv_path + ".smart.json"
    records = df_final.to_dict(orient='records')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"holdings": records}, f, indent=2, default=str)
        
    print(f"✅ Extracted {len(records)} items.")
    print(f"   Saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python universal_smart_loader.py <csv_path> <rules_json_path>")
    else:
        load_csv_with_rules(sys.argv[1], sys.argv[2])
