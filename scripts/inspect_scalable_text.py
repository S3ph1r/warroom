import fitz
import sys
from pathlib import Path

def dump_text(pdf_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        print(f"--- PAGE {i+1} ---")
        print(page.get_text("text")) # standard text
        # print(page.get_text("blocks")) # structured blocks if needed

if __name__ == "__main__":
    path = r"D:\Download\SCALABLE CAPITAL\20251219 Financial status Scalable Capital.pdf"
    if Path(path).exists():
        dump_text(path)
    else:
        print("File not found")
