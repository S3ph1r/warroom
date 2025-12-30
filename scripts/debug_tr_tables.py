import pdfplumber
import sys
from pathlib import Path

PDF_PATH = r"d:\Download\Trade Repubblic\Estratto conto.pdf"

def debug_tables():
    print(f"--- EXTRACTING TABLES FROM: {Path(PDF_PATH).name} ---")
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n--- PAGE {i+1} ---")
            tables = page.extract_tables()
            
            if not tables:
                print("No tables found.")
            else:
                for t_idx, table in enumerate(tables):
                    print(f"Table {t_idx+1} ({len(table)} rows):")
                    for row in table[:3]: # Print first 3 rows
                        print(row)
                    print("...")

if __name__ == "__main__":
    debug_tables()
