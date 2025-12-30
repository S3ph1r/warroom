import pdfplumber
import sys
from pathlib import Path

# Force UTF-8 for print
sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = r"d:\Download\Trade Repubblic\Estratto conto.pdf"

def inspect_pdf():
    print(f"--- INSPECTING: {Path(PDF_PATH).name} ---")
    try:
        with pdfplumber.open(PDF_PATH) as pdf:
            print(f"TOTAL PAGES: {len(pdf.pages)}")
            print("-" * 30)
            
            # Extract first 3 pages
            for i, page in enumerate(pdf.pages[:3]):
                print(f"--- PAGE {i+1} (LAYOUT=TRUE) ---")
                text = page.extract_text(layout=True)
                if text:
                    print(text)
                else:
                    print("[NO TEXT EXTRACTED]")
                print("-" * 30)
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    inspect_pdf()
