"""
Debug Scalable Text Layout
Dump raw text from a sample PDF to identify where the Amount fits in.
"""
from pathlib import Path
from pypdf import PdfReader
import re

PDF_PATH = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable\20230107 Monthly account statement Baader Bank.pdf")

def debug_text():
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        return

    reader = PdfReader(PDF_PATH)
    print(f"--- Parsing {PDF_PATH.name} ({len(reader.pages)} pages) ---")
    
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        full_text += text
        print(text)
        print("-" * 40)
        
    print("\n--- Search for 2022-12-20 ---")
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        if "2022-12-20" in line or "62.27" in line:
            print(f"Line {i}: {line}")

if __name__ == "__main__":
    debug_text()
