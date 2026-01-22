"""
Debug Income Parser
Test the Income statement parser with debug output.
"""
import uuid
import sys
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).parent.parent))

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20250506 Income statement Baader Bank pV94w5.pdf"

def parse_german_date(date_str):
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None

def parse_amount(num_str):
    s = num_str.strip()
    if not s: return Decimal(0)
    try:
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            s = s.replace(',', '.')
        return Decimal(s)
    except:
        return Decimal(0)

def debug_income():
    pdf_path = INBOX / TARGET
    
    print(f"Testing: {pdf_path.name}")
    print("=" * 60)
    
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    lines = full_text.split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Count how many times we see "Transaction:"
    tx_count = sum(1 for line in lines if "Transaction:" in line)
    print(f"Lines containing 'Transaction:': {tx_count}")
    
    # Show first few occurrences
    count = 0
    for i, line in enumerate(lines):
        if "Transaction:" in line:
            count += 1
            print(f"\nLine {i+1}: {line.strip()}")
            # Show next 15 lines
            for k in range(1, 16):
                if i+k < len(lines):
                    print(f"  +{k}: {lines[i+k].strip()}")
            
            if count >= 2:  # Just show first 2
                break

if __name__ == "__main__":
    debug_income()
