
import fitz
from pathlib import Path

pdf = Path(r"D:\Download\Trade Repubblic\Estratto conto.pdf")

if pdf.exists():
    doc = fitz.open(pdf)
    
    # Page 2
    if len(doc) > 1:
        page = doc[1]
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        text = "\n".join([b[4] for b in blocks])
        print("--- PAGE 2 TEXT (Block Sorted) ---")
        print(text[:2000])
    else:
        print("Only 1 page.")
