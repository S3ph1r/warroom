"""Analyze Encrypted Binance PDF"""
import pypdf
from pathlib import Path

fpath = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance\AccountStatementPeriod_10773818_20251216-20251217_d9522f326b11499f84f5e85f77195e60.pdf")
password = "66666666"

print(f"=== {fpath.name} ===")

try:
    reader = pypdf.PdfReader(fpath)
    if reader.is_encrypted:
        print(f"File is encrypted. Attempting decrypt...")
        reader.decrypt(password)
    
    print(f"Pages: {len(reader.pages)}")
    
    # Analyze first few pages
    for i in range(min(3, len(reader.pages))):
        text = reader.pages[i].extract_text()
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print('='*60)
        print(text[:1000])
        
        # Check for Holdings section keywords
        lower_text = text.lower()
        if "account balance" in lower_text or "estimated value" in lower_text or "wallet balance" in lower_text:
             print("\n[!] POTENTIAL HOLDINGS SNAPSHOT DETECTED")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
