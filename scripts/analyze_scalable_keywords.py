import os
import re
from pathlib import Path
from pypdf import PdfReader
from collections import Counter

# Set path (adjust if needed)
INBOX = Path(r"d:\Download\BGSAXO") # Using same root logic, but specific folder
SCALABLE_DIR = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

KNOWN_KEYWORDS = ["Purchase", "Sale", "Savings Plan", "Dividends", "Coupons/Dividends", "Coupons"]

def normalize_text(text):
    return text.replace('\n', ' ').strip()

def analyze_pdfs():
    print(f"Scanning {SCALABLE_DIR}...")
    
    files = list(SCALABLE_DIR.glob("*.pdf"))
    print(f"Found {len(files)} files.")
    
    isin_pattern = re.compile(r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b')
    
    missed_contexts = []
    all_operations = Counter()
    
    for pdf_file in files:
        # Check if Baader/Scalable (skip useless ones if any)
        if "Baader" not in pdf_file.name and "Scalable" not in pdf_file.name:
            continue
            
        try:
            reader = PdfReader(pdf_file)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            lines = full_text.split('\n')

            
            # Scan lines
            for i, line in enumerate(lines):
                line = line.strip()
                if not line: continue
                
                # Check for ISIN
                has_isin = isin_pattern.search(line)
                
                # Context scan (surrounding lines) if ISIN found
                if has_isin:
                    # Look at lines BEFORE the ISIN for potential Operation keyword
                    # Usually Op is 1-5 lines before or after
                    # Let's grab a window
                    start = max(0, i-5)
                    end = min(len(lines), i+5)
                    window = lines[start:end]
                    
                    # Check if any known keyword is in the window
                    found_known = False
                    for w in window:
                        if any(k in w for k in KNOWN_KEYWORDS):
                            found_known = True
                            # Track what we found just for stats
                            for k in KNOWN_KEYWORDS:
                                if k in w: all_operations[k] += 1
                            break
                    
                    if not found_known:
                        # This ISIN context has NO known keyword! Interesting!
                        context_str = " | ".join([l.strip() for l in window])
                        missed_contexts.append(f"{pdf_file.name} (L{i}): {context_str}")

        except Exception as e:
            print(f"Error reading {pdf_file.name}: {e}")

    print("\n✅ Analysis Complete.")
    print("="*60)
    print(f"Total ISIN occurrences with KNOWN keywords: {sum(all_operations.values())}")
    print(all_operations)
    print("="*60)
    print(f"Total ISIN occurrences with UNKNOWN keywords: {len(missed_contexts)}")
    print("="*60)
    
    # Print top unique missed contexts (simplified)
    # We'll print the first 50 detailed
    for idx, ctx in enumerate(missed_contexts[:100]):
        print(f"[{idx+1}] {ctx}")
        print("-" * 40)

if __name__ == "__main__":
    analyze_pdfs()
