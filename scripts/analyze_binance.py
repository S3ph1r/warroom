"""Analyze Binance files"""
import pandas as pd
import pypdf
from pathlib import Path
from io import StringIO

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance")

files = sorted(list(INBOX.glob("*")))

for fpath in files:
    print(f"\n{'='*70}")
    print(f"📂 {fpath.name} ({fpath.stat().st_size} bytes)")
    print('='*70)
    
    try:
        if fpath.suffix.lower() == '.csv':
            # Binance CSVs sometimes skip first rows or have specific delimiters
            try:
                df = pd.read_csv(fpath)
                print(f"CSV Standard Read:")
                print(f"  Rows: {len(df)} | Columns: {list(df.columns)}")
                if len(df) > 0:
                    print(f"  Sample: {df.iloc[0].to_dict()}")
            except:
                print("  Standard read failed, trying text preview...")
                with open(fpath, 'r', encoding='utf-8') as f:
                    print(f.read(500))
                    
        elif fpath.suffix.lower() == '.pdf':
            reader = pypdf.PdfReader(fpath)
            print(f"PDF Pages: {len(reader.pages)}")
            
            # Extract text from first page
            text = reader.pages[0].extract_text()
            print(f"\n--- PAGE 1 (first 800 chars) ---")
            print(text[:800])
            
            # Helper to check for keywords
            lower_text = text.lower()
            keywords = []
            if "total balance" in lower_text or "estimated value" in lower_text or "holding" in lower_text:
                keywords.append("HOLDINGS_SNAPSHOT")
            if "transaction" in lower_text or "history" in lower_text or "distribution" in lower_text:
                keywords.append("TRANSACTIONS")
                
            print(f"  Keywords detected: {keywords}")
            
    except Exception as e:
        print(f"  ERROR: {e}")
