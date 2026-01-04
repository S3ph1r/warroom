"""Analyze New Encrypted Binance PDF"""
import pypdf
from pathlib import Path

fpath = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance\AccountStatementPeriod_10773818_20250101-20260101_3b3ecab973f4498a995fbb70a755a181.pdf")
password = "66666666"

print(f"=== {fpath.name} ===")

try:
    reader = pypdf.PdfReader(fpath)
    if reader.is_encrypted:
        print(f"File is encrypted. Attempting decrypt...")
        reader.decrypt(password)
    
    print(f"Pages: {len(reader.pages)}")
    
    # Analyze first few pages
    for i in range(min(5, len(reader.pages))):
        text = reader.pages[i].extract_text()
        print(f"\n{'='*60}")
        print(f"PAGE {i+1}")
        print('='*60)
        print(text[:1500]) # First 1500 chars
        
        # Check for Holdings section keywords
        lower_text = text.lower()
        if "top 10" in lower_text:
             print("\n[!] DETECTED 'TOP 10' LIMITATION")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
