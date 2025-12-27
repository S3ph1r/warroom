
import fitz
from pathlib import Path

# Target the specific Crypto file
pdf = Path(r"D:\Download\Revolut\crypto-account-statement_2022-07-04_2025-12-20_it-it_1c330c.pdf")

if pdf.exists():
    doc = fitz.open(pdf)
    page = doc[0]
    
    # Use Block Sort
    blocks = page.get_text("blocks")
    blocks.sort(key=lambda b: (b[1], b[0]))
    text = "\n".join([b[4] for b in blocks])
    
    print(f"--- CRYPTO PAGE 1 TEXT (Block Sorted) ---")
    print(text[:2000])
else:
    print("File not found")
