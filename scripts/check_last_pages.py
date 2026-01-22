
import pdfplumber
from pathlib import Path

pdf_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    # Check last few pages
    for page_num in range(len(pdf.pages) - 5, len(pdf.pages)):
        page = pdf.pages[page_num]
        text = page.extract_text()
        print(f"\n{'='*60}")
        print(f"--- PAGE {page_num + 1} ---")
        print(f"{'='*60}")
        print(text[:2000] if text else "(empty)")
