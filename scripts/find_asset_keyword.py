import os
from pathlib import Path
from pypdf import PdfReader

SCALABLE_DIR = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGETS = ["XIAOMI", "D-WAVE", "QUANTUM", "KYG9830T1067", "US26740W1099"]

def search_targets():
    print(f"Searching targets {TARGETS} in {SCALABLE_DIR}...")
    files = list(SCALABLE_DIR.glob("*.pdf"))
    
    found_count = 0
    for pdf_file in files:
        try:
            reader = PdfReader(pdf_file)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                
                # Check if any target is in text
                if any(t in text.upper() for t in TARGETS):
                    print(f"\n🎯 FOUND MATCH in {pdf_file.name} (Page {i+1})")
                    print("="*60)
                    print(text)
                    print("="*60)
                    found_count += 1
                    if found_count >= 5: # Stop after finding a few examples
                        return
                        
        except Exception as e:
            print(f"Error {pdf_file.name}: {e}")

if __name__ == "__main__":
    search_targets()
