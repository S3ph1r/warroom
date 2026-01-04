import os
from pathlib import Path
from pypdf import PdfReader

SCALABLE_DIR = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
FILES_TO_INSPECT = [
    "20250704 Statement of accounts Baader Bank euAeZX.pdf", 
    "20251002 Securities account statement Broker Scalable Capital uhzy3V.pdf",
    "20251009 Corporate actions Baader Bank gyAhYE.pdf",
    "20241119 Securities announcement Baader Bank 97zb7v.pdf"
]

def inspect_types():
    print(f"Inspecting 4 representative files from {SCALABLE_DIR}...")
    
    for fname in FILES_TO_INSPECT:
        fpath = SCALABLE_DIR / fname
        if not fpath.exists():
            print(f"File not found: {fname}")
            continue
            
        print(f"\nFILE: {fname}")
        print("="*60)
        try:
            reader = PdfReader(fpath)
            # Dump first page only (usually enough to see type)
            text = reader.pages[0].extract_text()
            print(text[:2000]) # First 2000 chars
        except Exception as e:
            print(f"Error: {e}")
        print("="*60)

if __name__ == "__main__":
    inspect_types()
