
import fitz
from pathlib import Path

# Target the Cash file
pdf = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")
# Or the one in inbox?
inbox_pdf = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

target = pdf if pdf.exists() else inbox_pdf

if target.exists():
    doc = fitz.open(target)
    page = doc[0]
    
    # Block sort
    blocks = page.get_text("blocks")
    blocks.sort(key=lambda b: (b[1], b[0]))
    text = "\n".join([b[4] for b in blocks])
    
    print(f"--- CASH PAGE 1 ---")
    print(text[:2000])
else:
    print("File not found")
