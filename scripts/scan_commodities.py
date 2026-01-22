
import fitz
from pathlib import Path

SOURCE_DIR = Path(r"D:\Download\Revolut")

def main():
    print("SCANNING FOR COMMODITIES (XAU, XAG, GOLD, SILVER)")
    files = list(SOURCE_DIR.glob("*.pdf"))
    
    keywords = ["XAU", "XAG", "GOLD", "SILVER", "ORO", "ARGENTO", "PRECIOUS"]
    
    found_map = {}
    
    for pdf in files:
        print(f"Checking {pdf.name}...")
        try:
            doc = fitz.open(pdf)
            hits = []
            for i, page in enumerate(doc):
                text = page.get_text("text").upper()
                for k in keywords:
                    if k in text:
                        # Grab context around keyword
                        idx = text.find(k)
                        snippet = text[max(0, idx-50):min(len(text), idx+50)].replace("\n", " ")
                        hits.append(f"Page {i+1} [{k}]: ...{snippet}...")
            
            if hits:
                found_map[pdf.name] = hits
                print(f"  FOUND {len(hits)} hits!")
        except Exception as e:
            print(f"  Error: {e}")
            
    print("\n--- RESULTS ---")
    if not found_map:
        print("No Commodities found in any file.")
    else:
        for fname, hits in found_map.items():
            print(f"\nFILE: {fname}")
            for h in hits[:5]: # Show first 5
                print(f"  {h}")

if __name__ == "__main__":
    main()
