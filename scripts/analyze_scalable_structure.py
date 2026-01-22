import os
import re
from pathlib import Path
from pypdf import PdfReader
from collections import defaultdict

import sys
import codecs

# Force UTF-8 for Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

SCALABLE_DIR = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def analyze_scalable_docs():
    print(f"Analyzing Docs in {SCALABLE_DIR}...\n")
    
    files = list(SCALABLE_DIR.glob("*.pdf"))
    groups = defaultdict(list)
    
    # Group by name pattern
    for f in files:
        name = f.name
        # Simple heuristic: Split by "Baader Bank" or "Scalable Capital" or date
        # Example: "20250805 Securities Account Statement Broker Scalable Capital qzi98v.pdf"
        # Type is "Securities Account Statement Broker Scalable Capital"
        
        # Remove Date prefix (YYYYMMDD)
        clean_name = re.sub(r'^\d{8}\s+', '', name)
        # Remove hash suffix (last word usually)
        clean_name = re.sub(r'\s+[a-zA-Z0-9]{6}\.pdf$', '', clean_name)
        
        groups[clean_name].append(f)
        
    print(f"{'DOCUMENT TYPE':<60} | {'COUNT':<5}")
    print("-" * 70)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    for g_name, g_files in sorted_groups:
        print(f"{g_name:<60} | {len(g_files):<5}")
        
    print("\n" + "="*70)
    print("SEARCHING FOR DATA IN SAMPLES")
    print("="*70)
    
    # Inspect specific interesting types
    target_types = [
        "Securities Account Statement Broker Scalable Capital", # Potential Snapshot
        "Statement of accounts Baader Bank",                  # Potential Balance/Snapshot
        "Corporate actions Baader Bank",                      # Missing Transactions?
        "Income statement Baader Bank"                        # Dividends?
    ]
    
    for g_name, g_files in sorted_groups:
        # Check if relevant
        is_relevant = any(t.lower() in g_name.lower() for t in target_types)
        if not is_relevant and "Monthly" in g_name: continue # Skip Monthly (we know them)
        
        if g_files:
            sample = g_files[0] # Take most recent (sorted by glob usually? No, by date in name)
            # Find the most recent date
            sample = sorted(g_files, key=lambda x: x.name, reverse=True)[0]
            
            print(f"\n📄 TYPE: {g_name} (Sample: {sample.name})")
            print("-" * 60)
            try:
                reader = PdfReader(sample)
                text = ""
                for p in reader.pages[:2]: # First 2 pages
                    text += p.extract_text() + "\n"
                
                # ASCII only to avoid terminal errors
                clean_text = text.encode('ascii', 'ignore').decode('ascii')
                print(clean_text[:1000] + "...\n[TRUNCATED]")
                
                # Check for Keywords
                if "ISIN" in text: print("✅ Found 'ISIN'")
                if "Holdings" in text or "Position" in text or "Bestand" in text: print("✅ Found 'Holdings/Position'")
                if "Buy" in text or "Sell" in text or "Purchase" in text or "Sale" in text: print("✅ Found 'Buy/Sell'")
                
            except Exception as e:
                print(f"❌ Error reading: {e}")

if __name__ == "__main__":
    analyze_scalable_docs()
