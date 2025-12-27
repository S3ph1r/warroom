
import fitz
from pathlib import Path

files = list(Path(r"D:\Download\Revolut").glob("*.pdf"))

for path in files:
    print(f"\n{'='*50}")
    print(f"Inspecting: {path.name}")
    try:
        doc = fitz.open(path)
        print(f"Pages: {len(doc)}")
        
        print("\n--- PAGE 1 TEXT ---")
        print(doc[0].get_text("text")[:500])
        
        print("\n--- LAST PAGE TEXT ---")
        if len(doc) > 1:
            print(doc[-1].get_text("text")[:500])
    except Exception as e:
        print(f"Error: {e}")
