"""Debug: Show raw PDF text to inspect actual format"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

with pdfplumber.open(pdf_path) as pdf:
    # Page 2 (should have trades)
    print("=== PAGE 2 (first trades) ===")
    print(pdf.pages[1].extract_text()[:2000])
    
    # Page 82 (near end - should have deposit)
    print("\n\n=== PAGE 82-83 (deposits at end) ===")
    print(pdf.pages[81].extract_text())
    print("\n---")
    print(pdf.pages[82].extract_text())
    
    # Look for SELL operations
    print("\n\n=== SEARCHING FOR SELL PATTERNS ===")
    for i, page in enumerate(pdf.pages[:20]):
        text = page.extract_text() or ""
        if 'Vendi' in text or 'vendi' in text:
            print(f"Page {i+1}: Found 'Vendi'")
            # Show context
            idx = text.lower().find('vendi')
            print(f"  Context: ...{text[max(0,idx-50):idx+100]}...")
