import re
from pathlib import Path
from pypdf import PdfReader
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def exhaustive_search():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    isin = "KYG9830T1067"
    
    print(f"Exhaustive Search for Xiaomi (ISIN: {isin}) in {len(pdf_files)} files...")
    
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            page_count = len(reader.pages)
            for i in range(page_count):
                text = reader.pages[i].extract_text()
                if isin in text or "Xiaomi" in text:
                    print(f"\n>>> FOUND in {pdf.name} (Page {i+1})")
                    lines = text.split('\n')
                    for line in lines:
                        l = line.strip()
                        # Show lines with ISIN, Name, or quantities
                        if isin in l or "Xiaomi" in l or any(kw in l for kw in ["STK", "pz.", "Units", "Quantity", "100", "130"]):
                            print(f"  {l}")
        except Exception as e:
            pass

if __name__ == "__main__":
    exhaustive_search()
