"""
Debug Scalable Full Dump
Dump ALL text from the page containing '62.27' to understand layout.
"""
from pathlib import Path
from pypdf import PdfReader

PDF_PATH = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable\20230107 Monthly account statement Baader Bank.pdf")

def dump_full():
    if not PDF_PATH.exists():
        print(f"File not found: {PDF_PATH}")
        return

    reader = PdfReader(PDF_PATH)
    print(f"--- Parsing {PDF_PATH.name} ---")
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if "62.27" in text:
            print(f"--- PAGE {i+1} ---")
            print(text)
            print("--- END PAGE ---")
            
if __name__ == "__main__":
    dump_full()
