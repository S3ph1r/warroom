
import pdfplumber
from pathlib import Path

pdf_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

with pdfplumber.open(pdf_path) as pdf:
    # Page 83 (0-indexed = 82)
    page_num = 82
    if page_num < len(pdf.pages):
        page = pdf.pages[page_num]
        text = page.extract_text()
        print(f"--- PAGE {page_num + 1} ---")
        print(text)
    else:
        print(f"PDF has only {len(pdf.pages)} pages")
