"""
PDF to Excel Conversion using tabula-py

tabula-py uses Java-based Tabula to extract tables from PDFs.
This is much more robust than text parsing!
"""
import tabula
import pandas as pd
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

print("🔄 PDF to Excel Conversion")
print("=" * 60)
print(f"Source: {pdf_path.name}")
print()

# Extract ALL tables from ALL pages
print("📄 Extracting tables from PDF (this may take a moment)...")

try:
    # Method 1: Extract all tables
    tables = tabula.read_pdf(
        str(pdf_path), 
        pages='all',  # All 83 pages
        multiple_tables=True,
        pandas_options={'header': None}  # No header assumed
    )
    
    print(f"✅ Found {len(tables)} tables")
    
    if tables:
        # Combine all tables
        all_data = pd.concat(tables, ignore_index=True)
        print(f"📊 Total rows: {len(all_data)}")
        print(f"📊 Columns: {len(all_data.columns)}")
        
        # Show sample
        print("\nSample data (first 20 rows):")
        print(all_data.head(20).to_string())
        
        # Save to Excel
        excel_path = Path("data/extracted/BG_SAXO_Transactions.xlsx")
        all_data.to_excel(excel_path, index=False, header=False)
        print(f"\n💾 Saved to: {excel_path}")
        
        # Also save to CSV for easier inspection
        csv_path = Path("data/extracted/BG_SAXO_Transactions.csv")
        all_data.to_csv(csv_path, index=False, header=False)
        print(f"💾 Saved to: {csv_path}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nNote: tabula-py requires Java to be installed.")
    print("If Java is not installed, try:")
    print("  1. Install Java JDK 8+")
    print("  2. Or use alternative: pdfplumber custom extractor")
