"""
Debug Find Negative Quantity
Scans for 'STK -' or negative numbers which might indicate sales.
"""
from pathlib import Path
from pypdf import PdfReader
import re

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def scan_negative():
    print("=" * 60)
    print("🔎 SEARCHING FOR NEGATIVE QUANTITIES")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    files.sort(key=lambda x: x.name)
    
    hits = 0
    max_hits = 5
    
    for p in files:
        if hits >= max_hits: break
        
        try:
            reader = PdfReader(p)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
                
            lines = full_text.split('\n')
            
            for i, line in enumerate(lines):
                cleaned = line.strip()
                
                # Check for "STK -" pattern
                # Or just "-" followed by number on a short line
                
                is_match = False
                
                if "STK -" in cleaned or "Stk -" in cleaned:
                    is_match = True
                elif re.match(r'^-\s?[\d\.,]+$', cleaned): # "- 2" or "-2.000"
                    is_match = True
                    
                if is_match:
                    hits += 1
                    print(f"\n📂 FILE: {p.name}")
                    print(f"   MATCH: '{cleaned}'")
                    
                    start = max(0, i-4)
                    end = min(len(lines), i+5)
                    print(f"   --- Line {i+1} ---")
                    for k in range(start, end):
                        marker = ">>" if k == i else "  "
                        print(f"   {marker} {lines[k].strip()}")
                    print("   -------------------")
                    
                    if hits >= max_hits: break
                        
        except Exception as e:
            pass

    if hits == 0:
        print("\n❌ NO NEGATIVE QUANTITIES FOUND.")

if __name__ == "__main__":
    scan_negative()
