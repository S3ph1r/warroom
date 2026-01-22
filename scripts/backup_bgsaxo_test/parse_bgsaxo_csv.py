"""
BG SAXO CSV Parser - Pure Python (No LLM)

Parses the Posizioni CSV export from BG SAXO.
Handles summary rows (e.g., "Azioni (48)") by detecting:
1. Pattern match on first column: "Name (N)"
2. Empty Quantity column (index 3)

Column Mapping (from header analysis):
- 0: Strumento (Name)
- 2: Valuta (Currency)
- 3: Quantità (Quantity)
- 5: Prz. corrente (Current Price)
- 19: Ticker
- 36: ISIN
"""

import csv
import re
import json
from pathlib import Path
from tabulate import tabulate

def parse_bgsaxo_holdings(filepath):
    """Parse BG SAXO Posizioni CSV into structured holdings list."""
    items = []
    current_asset_type = "STOCK"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row
        
        for row in reader:
            if len(row) < 37:
                continue  # Skip malformed rows
            
            first_col = row[0].strip()
            quantity_col = row[3].strip()
            
            # Detect Summary Row: matches "Name (N)" pattern AND quantity is empty
            summary_match = re.match(r'^([A-Za-z /]+) \((\d+)\)$', first_col)
            if summary_match and not quantity_col:
                section_name = summary_match.group(1).upper()
                
                if "AZIONI" in section_name:
                    current_asset_type = "STOCK"
                elif "ETF" in section_name or "ETP" in section_name:
                    current_asset_type = "ETF"
                elif "OBBLIGAZIONI" in section_name:
                    current_asset_type = "BOND"
                elif "FONDI" in section_name:
                    current_asset_type = "FUND"
                elif "LIQUIDIT" in section_name:
                    current_asset_type = "CASH"
                
                print(f"📂 Section: {section_name} -> {current_asset_type}")
                continue
            
            # Parse Data Row
            try:
                # Handle italian number format (comma as decimal)
                qty_str = quantity_col.replace('.', '').replace(',', '.')
                qty = float(qty_str) if qty_str else 0
                
                price_str = row[5].replace('.', '').replace(',', '.') if row[5] else '0'
                price = float(price_str) if price_str else 0
                
                item = {
                    "name": first_col[:80],  # Truncate long names
                    "ticker": row[19].strip() if len(row) > 19 else "",
                    "isin": row[36].strip() if len(row) > 36 else "",
                    "quantity": qty,
                    "currency": row[2].strip(),
                    "current_price": price,
                    "asset_type": current_asset_type
                }
                
                # Only add if has valid ticker or name
                if item["ticker"] or item["name"]:
                    items.append(item)
                    
            except (ValueError, IndexError) as e:
                print(f"⚠️ Skipping row: {first_col[:30]}... Error: {e}")
                continue
    
    return items


def display_table(items):
    """Display extracted items as formatted table."""
    table_data = []
    for i, item in enumerate(items, 1):
        table_data.append([
            i,
            item["asset_type"],
            item["ticker"][:15] if item["ticker"] else "-",
            item["name"][:30],
            item["quantity"],
            item["currency"],
            item["isin"] if item["isin"] else "-"
        ])
    
    headers = ["#", "Type", "Ticker", "Name", "Qty", "Cur", "ISIN"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def save_json(items, output_path):
    """Save items to JSON file."""
    output = {
        "broker": "bgsaxo",
        "strategy": "Python Direct Parse",
        "items_count": len(items),
        "data": items
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved {len(items)} items to {output_path}")


if __name__ == "__main__":
    # Source file
    csv_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv")
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        exit(1)
    
    print(f"📄 Parsing: {csv_path.name}\n")
    
    # Parse
    items = parse_bgsaxo_holdings(csv_path)
    
    # Display
    print(f"\n📊 Extracted {len(items)} holdings:\n")
    display_table(items)
    
    # Save
    output_path = Path(__file__).parent.parent / "data" / "extracted" / "BG_SAXO_Holdings_Python.json"
    save_json(items, output_path)
