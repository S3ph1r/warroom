"""
Deep Analysis of BG SAXO Documents
Extracts and displays full structure and sample data.
"""
import pandas as pd
import fitz
from pathlib import Path

BGSAXO_FOLDER = Path(r"D:\Download\BGSAXO")

def analyze_csv(file_path):
    print(f"\n{'='*80}")
    print(f"FILE: {file_path.name}")
    print(f"SIZE: {file_path.stat().st_size / 1024:.1f} KB")
    print('='*80)
    
    try:
        # Read with auto-detect separator
        df = pd.read_csv(file_path, sep=None, engine='python')
        
        print(f"\nROWS: {len(df)}")
        print(f"COLUMNS ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            # Clean column name for display
            clean_col = col.replace('\ufeff', '').replace('"', '').strip()
            # Sample value
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
            print(f"  {i:2}. {clean_col:<30} | Sample: {str(sample)[:50]}")
        
        print("\n--- FIRST 5 ROWS (Key Columns) ---")
        # Select key columns if they exist
        key_cols = []
        for c in df.columns:
            clean = c.lower().replace('\ufeff', '').replace('"', '')
            if any(k in clean for k in ['strumento', 'isin', 'quantità', 'quantity', 'prezzo', 'valuta', 'valore']):
                key_cols.append(c)
        
        if key_cols:
            print(df[key_cols].head().to_string())
        else:
            print(df.iloc[:5, :6].to_string())  # First 6 columns
            
        print("\n--- LAST 5 ROWS ---")
        if key_cols:
            print(df[key_cols].tail().to_string())
        else:
            print(df.iloc[-5:, :6].to_string())
            
    except Exception as e:
        print(f"ERROR: {e}")

def analyze_pdf(file_path, max_pages=3):
    print(f"\n{'='*80}")
    print(f"FILE: {file_path.name}")
    print(f"SIZE: {file_path.stat().st_size / 1024:.1f} KB")
    print('='*80)
    
    try:
        doc = fitz.open(file_path)
        print(f"PAGES: {len(doc)}")
        
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            print(f"\n--- PAGE {page_num + 1} ---")
            
            # Try to find tables
            tabs = page.find_tables()
            if tabs.tables:
                print(f"TABLES FOUND: {len(tabs.tables)}")
                for i, tab in enumerate(tabs.tables):
                    print(f"\nTable {i+1}:")
                    md = tab.to_markdown()
                    # Show first 500 chars
                    print(md[:800] if len(md) > 800 else md)
            else:
                print("NO TABLES FOUND. Text extract:")
                text = page.get_text("text")
                print(text[:1000] if len(text) > 1000 else text)
                
        doc.close()
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Analyze latest CSV
    csv_file = BGSAXO_FOLDER / "Posizioni_19-dic-2025_17_49_12.csv"
    analyze_csv(csv_file)
    
    # Analyze latest Transaction PDF
    pdf_file = BGSAXO_FOLDER / "Transactions_19807401_2025-01-01_2025-12-19.pdf"
    analyze_pdf(pdf_file)
