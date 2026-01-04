"""
Find Nvidia SELL in Income Statement
Specifically search for the Nvidia SELL transaction (7 units).
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20250506 Income statement Baader Bank pV94w5.pdf"

def find_nvidia_sell():
    pdf_path = INBOX / TARGET
    
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    lines = full_text.split('\n')
    
    # Look for WWUM 00407373754 (the Nvidia SELL transaction ID from scan)
    for i, line in enumerate(lines):
        if "WWUM 00407373754" in line or ("nvidia" in line.lower() and "7" in lines[i:i+10]):
            start = max(0, i-5)
            end = min(len(lines), i+20)
            print(f"\n{'='*60}")
            print(f"Found at line {i+1}:")
            print('='*60)
            for k in range(start, end):
                marker = ">>" if k == i else "  "
                print(f"{marker} L{k+1}: {lines[k].strip()}")

if __name__ == "__main__":
    find_nvidia_sell()
