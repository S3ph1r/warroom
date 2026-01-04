"""
Debug Scan for Nvidia
Scans all Scalable PDFs for Nvidia mentions to find all transactions.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
KEYWORDS = ["Nvidia", "NVIDIA", "US67066G1040"]

def scan_nvidia():
    print("=" * 60)
    print(f"🔎 SCANNING FOR: {KEYWORDS}")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    files.sort(key=lambda x: x.name)
    
    hits = 0
    
    for p in files:
        try:
            reader = PdfReader(p)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
                
            lines = full_text.split('\n')
            found_in_file = False
            
            for i, line in enumerate(lines):
                if any(k.lower() in line.lower() for k in KEYWORDS):
                    if not found_in_file:
                        print(f"\n📂 FILE: {p.name}")
                        found_in_file = True
                    
                    hits += 1
                    start = max(0, i-4)
                    end = min(len(lines), i+5)
                    
                    print(f"   --- Line {i+1} ---")
                    for k in range(start, end):
                        marker = ">>" if k == i else "  "
                        print(f"   {marker} {lines[k].strip()}")
                    print("   -------------------")
                    
        except Exception as e:
            pass
            
    print(f"\nTotal Hits: {hits}")

if __name__ == "__main__":
    scan_nvidia()
