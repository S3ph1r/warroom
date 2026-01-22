"""
Test PDF Table Extraction approaches

1. pdfplumber.extract_tables() - native Python
2. Show what structure we can get from the PDF

If tables are extractable, we can parse them deterministically!
"""
import pdfplumber
from pathlib import Path
import pandas as pd

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

print("🔍 PDF Table Extraction Test")
print("=" * 60)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Try extracting tables from first few pages
    all_tables = []
    
    for i, page in enumerate(pdf.pages[:5]):  # First 5 pages
        tables = page.extract_tables()
        print(f"\n📄 Page {i+1}: Found {len(tables)} table(s)")
        
        for j, table in enumerate(tables):
            if table:
                print(f"  Table {j+1}: {len(table)} rows x {len(table[0]) if table else 0} cols")
                # Show first 3 rows
                for row in table[:3]:
                    print(f"    {row}")
                all_tables.extend(table)
    
    print("\n" + "=" * 60)
    print(f"📊 Total rows from first 5 pages: {len(all_tables)}")
    
    # Also try page 82-83 (deposits)
    print("\n📄 Pages 82-83 (deposits):")
    for i in [81, 82]:
        tables = pdf.pages[i].extract_tables()
        print(f"  Page {i+1}: {len(tables)} table(s)")
        for table in tables:
            if table:
                print(f"    Rows: {len(table)}")
                for row in table[:5]:
                    print(f"      {row}")
