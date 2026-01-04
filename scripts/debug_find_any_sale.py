"""
Debug Find Any Sale
Scans all Scalable PDFs for generic Sale keywords to identify how sales are recorded.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
# Keywords for Sales (English, German, Italian)
KEYWORDS = ["Sale", "Verkauf", "Vendita", "Sold", "Ausgang", "Transfer Out", "Uscita"]

def scan_for_sales():
    print("=" * 60)
    print(f"🔎 SCANNING FOR SALES KEYWORDS: {KEYWORDS}")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    files.sort(key=lambda x: x.name)
    
    hits = 0
    max_hits = 10 # Just find a few examples
    
    for p in files:
        if hits >= max_hits: break
        
        try:
            reader = PdfReader(p)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
                
            lines = full_text.split('\n')
            
            for i, line in enumerate(lines):
                # Check for exact keyword match (case insensitive)
                # Avoid "Sale" inside other words if possible, but strict check first
                line_lower = line.lower().strip()
                
                match = None
                for k in KEYWORDS:
                    if k.lower() == line_lower or k.lower() in line_lower.split():
                        match = k
                        break
                
                if match:
                    hits += 1
                    print(f"\n📂 FILE: {p.name}")
                    print(f"   MATCH: '{match}'")
                    # Print Context
                    start = max(0, i-4)
                    end = min(len(lines), i+5)
                    print(f"   --- Line {i+1} ---")
                    for k in range(start, end):
                        marker = ">>" if k == i else "  "
                        print(f"   {marker} {lines[k].strip()}")
                    print("   -------------------")
                    
                    if hits >= max_hits: break
                    
        except Exception as e:
            # print(f"❌ Error reading {p.name}: {e}")
            pass
            
    if hits == 0:
        print("\n❌ NO SALES TRANSACTIONS FOUND IN ANY FILE.")
    else:
        print(f"\n✅ Found {hits} examples.")

if __name__ == "__main__":
    scan_for_sales()
