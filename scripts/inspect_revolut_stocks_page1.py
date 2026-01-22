
import fitz
from pathlib import Path

# Target the specific file
SOURCE_DIR = Path(r"D:\Download\Revolut")
TARGET_FILE = "trading-account-statement_2019-12-28_2025-12-26_it-it_e34cc5.pdf"
path = SOURCE_DIR / TARGET_FILE

if path.exists():
    doc = fitz.open(path)
    page = doc[0]
    
    # Use Block Sort Logic from extract_all_transactions.py
    blocks = page.get_text("blocks")
    blocks.sort(key=lambda b: (b[1], b[0]))
    text = "\n".join([b[4] for b in blocks])
    
    print(f"--- PAGE 1 TEXT (Block Sorted) ---")
    print(text[:2000])
else:
    print("File not found")
