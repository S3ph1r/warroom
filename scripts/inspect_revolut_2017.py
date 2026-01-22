
import fitz
from pathlib import Path

path = Path(r"g:/Il mio Drive/WAR_ROOM_DATA/inbox/revolut/account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")

if path.exists():
    print(f"Inspecting: {path.name}")
    doc = fitz.open(path)
    print(f"Pages: {len(doc)}")
    
    # Check first few pages
    print("\n--- PAGE 1 TEXT ---")
    print(doc[0].get_text("text")[:800])
    
    # Scan for keywords in first 5 pages
    full_text = ""
    for i in range(min(5, len(doc))):
        full_text += doc[i].get_text("text")
        
    print("\n--- KEYWORD CHECK ---")
    keywords = ["Symbol", "ISIN", "Quantity", "Price", "Share", "Dividen", "Azioni"]
    found = [k for k in keywords if k.upper() in full_text.upper()]
    print(f"Found Keywords: {found}")

else:
    print("File not found")
