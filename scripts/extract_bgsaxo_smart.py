"""
Smart BG SAXO Ingestion Script
==============================
1. Analyzes all files in BG SAXO folder
2. Identifies document type (Holdings/Transactions) based on filename
3. For CSV/Excel: Uses pandas parser (more reliable)
4. For PDF: Uses LLM extraction
5. Outputs structured JSON per document type
"""
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Configuration
BGSAXO_FOLDER = Path(r'D:\Download\BGSAXO')
OUTPUT_FOLDER = Path(__file__).parent.parent / 'data' / 'extracted' / 'bgsaxo'
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def analyze_files():
    """List and classify all files in BG SAXO folder."""
    print("=" * 60)
    print("BG SAXO FILE ANALYSIS")
    print("=" * 60)
    
    files = list(BGSAXO_FOLDER.glob('*'))
    
    holdings_files = []
    transaction_files = []
    
    for f in files:
        name = f.name.lower()
        
        # Classify by filename pattern
        if 'posizioni' in name or 'positions' in name or 'holdings' in name:
            doc_type = 'HOLDINGS'
            holdings_files.append(f)
        elif 'transaction' in name or 'trades' in name:
            doc_type = 'TRANSACTIONS'
            transaction_files.append(f)
        else:
            doc_type = 'UNKNOWN'
        
        ext = f.suffix.upper()
        print(f"  [{doc_type:12}] [{ext:5}] {f.name}")
    
    print()
    print(f"Holdings files: {len(holdings_files)}")
    print(f"Transaction files: {len(transaction_files)}")
    
    return holdings_files, transaction_files


def extract_date_from_filename(filename: str) -> str:
    """Extract date from BG SAXO filename format: Posizioni_19-dic-2025_17_49_12.csv"""
    import re
    
    # Pattern: dd-mmm-yyyy
    months = {'gen':'01', 'feb':'02', 'mar':'03', 'apr':'04', 'mag':'05', 'giu':'06',
              'lug':'07', 'ago':'08', 'set':'09', 'ott':'10', 'nov':'11', 'dic':'12'}
    
    match = re.search(r'(\d{2})-(\w{3})-(\d{4})', filename.lower())
    if match:
        day, month_it, year = match.groups()
        month = months.get(month_it, '01')
        return f"{year}-{month}-{day}"
    
    return datetime.now().strftime('%Y-%m-%d')


def parse_bgsaxo_csv(filepath: Path) -> dict:
    """
    Parse BG SAXO Posizioni CSV file.
    Returns structured holdings data.
    """
    print(f"\n--- Parsing CSV: {filepath.name} ---")
    
    try:
        # BG SAXO CSV uses semicolon separator and has specific structure
        df = pd.read_csv(filepath, sep=';', encoding='utf-8')
        
        print(f"Columns found: {list(df.columns)}")
        print(f"Rows: {len(df)}")
        
        # Show first few rows for debugging
        print("\nSample data:")
        print(df.head(3).to_string())
        
        # Map columns (BG SAXO uses Italian names)
        column_map = {
            'Simbolo': 'ticker',
            'ISIN': 'isin',
            'Descrizione': 'name',
            'Quantità': 'quantity',
            'Prezzo medio': 'purchase_price',
            'Valore di mercato': 'current_value',
            'Valuta': 'currency',
            'Tipo': 'asset_type',
        }
        
        holdings = []
        
        for _, row in df.iterrows():
            # Skip empty rows or headers
            ticker = str(row.get('Simbolo', '')).strip()
            if not ticker or ticker == 'nan' or ticker == 'Simbolo':
                continue
            
            # Extract required fields
            holding = {
                'ticker': ticker,
                'isin': str(row.get('ISIN', '')).strip() if pd.notna(row.get('ISIN')) else None,
                'name': str(row.get('Descrizione', '')).strip() if pd.notna(row.get('Descrizione')) else ticker,
                'currency': str(row.get('Valuta', 'EUR')).strip() if pd.notna(row.get('Valuta')) else 'EUR',
            }
            
            # Parse quantity (handle comma as decimal separator)
            qty_str = str(row.get('Quantità', '0')).replace('.', '').replace(',', '.')
            try:
                holding['quantity'] = float(qty_str)
            except:
                holding['quantity'] = 0.0
            
            # Optional: purchase price
            price_str = str(row.get('Prezzo medio', '0')).replace('.', '').replace(',', '.')
            try:
                holding['purchase_price'] = float(price_str) if price_str != '0' else None
            except:
                holding['purchase_price'] = None
            
            # Optional: current value
            value_str = str(row.get('Valore di mercato', '0')).replace('.', '').replace(',', '.')
            try:
                holding['current_value'] = float(value_str) if value_str != '0' else None
            except:
                holding['current_value'] = None
            
            # Skip if no quantity
            if holding['quantity'] > 0:
                holdings.append(holding)
        
        result = {
            'broker': 'BG_SAXO',
            'document_type': 'holdings',
            'extraction_date': extract_date_from_filename(filepath.name),
            'source_file': filepath.name,
            'holdings': holdings,
            'total_holdings': len(holdings),
            'extraction_method': 'csv_parser'
        }
        
        print(f"\n✅ Extracted {len(holdings)} holdings")
        
        return result
        
    except Exception as e:
        print(f"❌ Error parsing CSV: {e}")
        return None


def parse_bgsaxo_excel(filepath: Path) -> dict:
    """Parse BG SAXO Excel file."""
    print(f"\n--- Parsing Excel: {filepath.name} ---")
    
    try:
        df = pd.read_excel(filepath)
        print(f"Columns: {list(df.columns)}")
        print(f"Rows: {len(df)}")
        
        # Similar logic to CSV parser
        # ... (would implement if needed)
        
        return None  # TODO: implement if CSV fails
        
    except Exception as e:
        print(f"❌ Error parsing Excel: {e}")
        return None


def main():
    """Main extraction flow for BG SAXO."""
    holdings_files, transaction_files = analyze_files()
    
    # Focus on the MOST RECENT holdings file
    if holdings_files:
        # Sort by name to get most recent (assumes date in filename)
        holdings_files.sort(key=lambda x: x.name, reverse=True)
        latest_holdings = holdings_files[0]
        
        print(f"\n>>> Processing LATEST holdings file: {latest_holdings.name}")
        
        if latest_holdings.suffix.lower() == '.csv':
            result = parse_bgsaxo_csv(latest_holdings)
        elif latest_holdings.suffix.lower() in ['.xlsx', '.xls']:
            result = parse_bgsaxo_excel(latest_holdings)
        else:
            print("Unsupported format for holdings")
            result = None
        
        if result:
            # Save to JSON
            output_path = OUTPUT_FOLDER / 'bgsaxo_holdings.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Saved to: {output_path}")
            
            # Summary
            print("\n" + "=" * 60)
            print("EXTRACTION SUMMARY")
            print("=" * 60)
            print(f"Broker: {result['broker']}")
            print(f"Date: {result['extraction_date']}")
            print(f"Holdings: {result['total_holdings']}")
            print(f"Method: {result['extraction_method']}")
            
            # Show sample
            print("\nSample holdings (first 5):")
            for h in result['holdings'][:5]:
                print(f"  {h['ticker']:10} | {h.get('isin', 'N/A'):12} | {h['currency']:3} | Qty: {h['quantity']}")


if __name__ == "__main__":
    main()
