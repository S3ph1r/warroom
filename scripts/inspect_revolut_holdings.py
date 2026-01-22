
import fitz
from pathlib import Path

# Check Trading and Crypto statements
files = list(Path(r"D:\Download\Revolut").glob("*statement*.pdf"))

# Filter for relevant ones
target_files = [f for f in files if "trading-account" in f.name or "crypto-account" in f.name]

for path in target_files:
    print(f"\n{'='*50}")
    print(f"Inspecting: {path.name}")
    try:
        doc = fitz.open(path)
        pages = len(doc)
        print(f"Total Pages: {pages}")
        
        # Check First Page (Header)
        print("--- HEADER ---")
        print(doc[0].get_text("text")[:300])
        
        # Check Last Page (Summary?)
        print("--- FOOTER/LAST PAGE ---")
        print(doc[-1].get_text("text")[:500])
        
    except Exception as e:
        print(f"Error: {e}")
