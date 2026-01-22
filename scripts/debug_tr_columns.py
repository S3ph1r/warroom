import pdfplumber
from pathlib import Path

PDF_PATH = Path(r"d:\Download\Trade Repubblic\Estratto conto.pdf")

with pdfplumber.open(PDF_PATH) as pdf:
    page = pdf.pages[1]  # Page 2
    
    # Try to define table explicitly with column boundaries
    # Based on the visual layout: DATE (0-80) | TYPE (80-130) | DESCRIPTION (130-420) | IN (420-480) | OUT (480-520) | BALANCE (520-)
    table_settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "text",
        "explicit_vertical_lines": [80, 130, 420, 480, 520],  # Column separators
    }
    
    tables = page.extract_tables(table_settings)
    print(f"Found {len(tables)} tables with explicit columns")
    
    if tables:
        for i, table in enumerate(tables):
            print(f"\n=== Table {i+1}: {len(table)} rows ===")
            for row_idx, row in enumerate(table[:10]):  # First 10 rows
                print(f"Row {row_idx}: {row}")
