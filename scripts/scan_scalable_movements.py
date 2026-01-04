import sys
import codecs
from pypdf import PdfReader
from pathlib import Path
import re
from collections import Counter

# Force UTF-8 for Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

SCALABLE_DIR = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

# Keywords to look for (EN, IT, DE-adjacent)
KEYWORDS = [
    r"Purchase", r"Sale", r"Compravendita", r"Acquisto", r"Vendita", 
    r"Dividendo", r"Dividend", r"Distribuzione", r"Distribution",
    r"Split", r"Assegnazione", r"Removal", r"Entry", r"Booking",
    r"Kauf", r"Verkauf", r"Dividende", r"Gutschrift", r"Belastung"
]

def scan_all_for_movements():
    print(f"Scanning 92 files for movements in {SCALABLE_DIR}...\n")
    files = list(SCALABLE_DIR.glob("*.pdf"))
    
    file_type_stats = Counter()
    movement_hits = []
    
    for pdf_file in files:
        # Determine group type (simplified)
        clean_name = re.sub(r'^\d{8}\s+', '', pdf_file.name)
        clean_name = re.sub(r'\s+[a-zA-Z0-9]{6}\.pdf$', '', clean_name)
        
        try:
            reader = PdfReader(pdf_file)
            has_movements = False
            found_keywords = set()
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text: continue
                
                for kw in KEYWORDS:
                    if re.search(kw, text, re.IGNORECASE):
                        found_keywords.add(kw)
                        has_movements = True
            
            if has_movements:
                file_type_stats[clean_name] += 1
                movement_hits.append({
                    "file": pdf_file.name,
                    "type": clean_name,
                    "keywords": list(found_keywords)
                })
                
        except Exception as e:
            print(f"Error {pdf_file.name}: {e}")

    print("\nSUMMARY OF FILES WITH POTENTIAL MOVEMENTS:")
    print("-" * 70)
    for g_name, count in file_type_stats.most_common():
        print(f"{g_name:<60} | {count}")
        
    print("\nDETAILED SAMPLES (First 20):")
    print("-" * 70)
    for hit in movement_hits[:20]:
        print(f"File: {hit['file']}")
        print(f"Type: {hit['type']}")
        print(f"Keywords Found: {', '.join(hit['keywords'])}")
        print("-" * 40)

if __name__ == "__main__":
    scan_all_for_movements()
