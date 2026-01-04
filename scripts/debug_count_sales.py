"""
Debug Count Sales
Count how many "Sale" lines exist and their positions in 20241207 file.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20241207 Monthly account statement Baader Bank nAW1Ve.pdf"

def count_sales():
    pdf_path = INBOX / TARGET
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    lines = full_text.split('\n')
    
    print(f"Total Lines: {len(lines)}")
    print("\nAll lines with 'Sale':")
    
    for i, line in enumerate(lines):
        if line.strip() == "Sale":
            print(f"\n{'='*40}")
            print(f"SALE at Line {i+1}:")
            # Print context
            start = max(0, i-3)
            end = min(len(lines), i+8)
            for k in range(start, end):
                marker = ">>" if k == i else "  "
                print(f"  {marker} L{k+1}: {lines[k].strip()}")

if __name__ == "__main__":
    count_sales()
