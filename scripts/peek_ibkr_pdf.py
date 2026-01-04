"""Peek at Open Positions section in IBKR PDF"""
from pypdf import PdfReader
from pathlib import Path
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\ibkr\Rendiconto di attività.pdf")

try:
    reader = PdfReader(PDF_PATH)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    # Locate "Posizioni aperte" or "Open Positions"
    # It might be a header.
    # Let's find the start index and print the next 2000 chars
    
    match = re.search(r"(Posizioni aperte|Open Positions)", full_text, re.IGNORECASE)
    if match:
        print(f"--- FOND SECTION: {match.group(1)} ---")
        start_idx = match.start()
        print(full_text[start_idx:start_idx+3000])
    else:
        print("❌ Section 'Posizioni aperte' not found via regex.")
        # Print first 2 pages just in case
        print("--- DUMPING FIRST 2000 CHARS ---")
        print(full_text[:2000])
        
except Exception as e:
    print(f"Error: {e}")
