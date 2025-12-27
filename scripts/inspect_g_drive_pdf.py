
import fitz
from pathlib import Path

path = Path(r"g:/Il mio Drive/WAR_ROOM_DATA/account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

if path.exists():
    print(f"Inspecting: {path.name}")
    doc = fitz.open(path)
    print(f"Pages: {len(doc)}")
    
    print("\n--- PAGE 1 ---")
    print(doc[0].get_text("text")[:800])
    
    # Check for keywords
    full_text = ""
    for i in range(min(3, len(doc))): # First 3 pages
        full_text += doc[i].get_text("text")
        
    keywords = ["Stock", "Trading", "Share", "Azioni", "Crypto", "Bitcoin"]
    found = [k for k in keywords if k.upper() in full_text.upper()]
    print(f"\nKeywords found in first 3 pages: {found}")
    
else:
    print(f"File not found: {path}")
