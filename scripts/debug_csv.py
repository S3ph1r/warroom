"""Debug BG Saxo CSV parsing"""
import csv
from decimal import Decimal

csv_path = r'D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv'

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    for i, row in enumerate(reader):
        strumento = row.get('Strumento', '').strip()
        
        # Skip header rows
        if strumento and not strumento.startswith('Azioni') and not strumento.startswith('ETP'):
            # Show first 3 data rows
            if i < 10:
                print(f"\n=== Row {i} ===")
                print(f"Strumento: {strumento[:30]}")
                
                espo_key = 'Esposizione (EUR)'
                espo_raw = row.get(espo_key, 'NOT_FOUND')
                print(f"Esposizione (EUR): '{espo_raw}'")
                
                qty_raw = row.get('Quantità', 'NOT_FOUND')
                print(f"Quantità: '{qty_raw}'")
                
                ticker = row.get('Ticker', 'NOT_FOUND')
                print(f"Ticker: '{ticker}'")

# Also show all column names
print("\n=== COLUMN NAMES ===")
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for i, col in enumerate(reader.fieldnames):
        print(f"{i}: '{col}'")
