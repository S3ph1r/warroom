"""
Debug Find Specific Sale Transaction
Scans for "Sale" or "Verkauf" appearing in a transaction context (near a date or amount).
"""
from pathlib import Path
from pypdf import PdfReader
import re

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
KEYWORDS = ["Sale", "Verkauf", "Uscita"]

def scan_txs():
    print("=" * 60)
    print("🔎 SEARCHING FOR 'SALE' TRANSACTIONS")
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
                
                # Check for keyword exactly
                is_match = False
                if cleaned in KEYWORDS:
                    is_match = True
                elif any(k in cleaned for k in KEYWORDS) and len(cleaned) < 20: # Short line with keyword
                    is_match = True
                    
                if is_match:
                    # Verify context: check previous lines for Date
                    has_date = False
                    for k in range(1, 4):
                        if i-k >= 0:
                            prev = lines[i-k].strip()
                            if re.match(r'\d{4}-\d{2}-\d{2}', prev) or re.match(r'\d{2}\.\d{2}\.\d{4}', prev):
                                has_date = True
                    
                    if has_date:
                        hits += 1
                        print(f"\n📂 FILE: {p.name}")
                        print(f"   MATCH: '{cleaned}' (Context Verified)")
                        
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
        print("\n❌ NO CONFIRMED SALE TRANSACTIONS FOUND.")

if __name__ == "__main__":
    scan_txs()
