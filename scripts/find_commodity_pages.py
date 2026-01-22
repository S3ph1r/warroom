
import fitz
from pathlib import Path

pdf = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

if pdf.exists():
    doc = fitz.open(pdf)
    print(f"Total Pages: {len(doc)}")
    
    for i, page in enumerate(doc):
        text = page.get_text("text").upper()
        if "ESTRATTO CONTO IN XAU" in text or "ESTRATTO CONTO IN XAG" in text:
            print(f"--- FOUND HEADER ON PAGE {i+1} ---")
            
            # Now dump block-sorted text for this page
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            clean_text = "\n".join([b[4] for b in blocks])
            print(clean_text[:1500])
            
else:
    print("File not found")
