"""Analyze IBKR CSV and PDF"""
import pandas as pd
from pathlib import Path
from pypdf import PdfReader
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\ibkr")
CSV_PATH = BASE_DIR / "U22156212.TRANSACTIONS.1Y.csv"
PDF_PATH = BASE_DIR / "Rendiconto di attività.pdf"

print(f"=== ANALYZING CSV: {CSV_PATH.name} ===")
try:
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        print("First 10 lines (Raw):")
        for _ in range(10):
            print(f.readline().strip())
            
    # Attempt parsing with header skip (IBKR CSVs often have preamble)
    # usually "Statement" line, "Header" line, "Data" line
    # Let's try to just dump raw first to understand structure
        
except Exception as e:
    print(f"❌ Error reading CSV: {e}")

print(f"\n\n=== ANALYZING PDF: {PDF_PATH.name} ===")
try:
    reader = PdfReader(PDF_PATH)
    print(f"Pages: {len(reader.pages)}")
    print("--- Page 1 Text ---")
    print(reader.pages[0].extract_text()[:1000])
    
    # Check for specific sections in text
    full_text = ""
    for i in range(min(5, len(reader.pages))):
        full_text += reader.pages[i].extract_text()
        
    print("\n--- Key Sections Found? ---")
    print(f"Posizioni aperte (Open Positions): {'Posizioni aperte' in full_text or 'Open Positions' in full_text}")
    print(f"Operazioni (Trades): {'Operazioni' in full_text or 'Trades' in full_text}")
    print(f"Depositi (Deposits): {'Depositi' in full_text or 'Deposits' in full_text}")
    
except Exception as e:
    print(f"❌ Error reading PDF: {e}")
