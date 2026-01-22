"""Analyze page 83 (first deposit) to understand format"""
import pdfplumber
from pathlib import Path

pdf_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf")

with pdfplumber.open(pdf_path) as pdf:
    # Page 83 (0-indexed = 82)
    page = pdf.pages[82]
    text = page.extract_text()
    
    print(f"=== PAGE 83 (First Deposit) ===")
    print(f"Characters: {len(text)}")
    print()
    print(text)
    print()
    print("=" * 50)
    
    # Also check page 80-82 for more context
    for i in range(79, 83):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        print(f"\n=== PAGE {i+1} ({len(text)} chars) ===")
        print(text[:1000] if text else "(empty)")
