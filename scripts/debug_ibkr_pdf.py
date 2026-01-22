"""Debug IBKR PDF - Find Tickers"""
from pypdf import PdfReader
from pathlib import Path
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\ibkr\Rendiconto di attività.pdf")
TARGETS = ["RGTI", "3CP", "UAMY"]

try:
    reader = PdfReader(PDF_PATH)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
        
    print(f"Total Length: {len(full_text)}")
    
    for t in TARGETS:
        print(f"\n--- SEARCHING FOR: {t} ---")
        matches = [m.start() for m in re.finditer(re.escape(t), full_text)]
        
        if not matches:
            print("❌ Not found")
        else:
            for m in matches:
                start = max(0, m - 100)
                end = min(len(full_text), m + 300)
                context = full_text[start:end].replace('\n', ' [NL] ')
                print(f"📍 Found at {m}:")
                print(f"...{context}...")
                print("-" * 40)

except Exception as e:
    print(f"Error: {e}")
