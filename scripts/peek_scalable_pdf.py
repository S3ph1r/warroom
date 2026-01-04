"""Peek at Scalable Capital / Baader Bank PDF"""
from pypdf import PdfReader
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Sample file (recent monthly statement)
PDF_PATH = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable\20241106 Monthly account statement Baader Bank.pdf")

print(f"=== ANALYZING PDF: {PDF_PATH.name} ===")
try:
    reader = PdfReader(PDF_PATH)
    print(f"Pages: {len(reader.pages)}")
    
    for i, page in enumerate(reader.pages):
        print(f"\n--- Page {i+1} ---")
        text = page.extract_text()
        print(text[:2000]) # First 2000 chars
        
except Exception as e:
    print(f"❌ Error reading PDF: {e}")
