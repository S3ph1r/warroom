import re
from pathlib import Path
from pypdf import PdfReader
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def find_missing_movements():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    # Target dates from fiscal report
    targets = ["27.12.2024", "30.12.2024", "KYG9830T1067", "Xiaomi"]
    
    print(f"Searching for Xiaomi movements in {len(pdf_files)} files...")
    
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            page_text = ""
            for i, page in enumerate(reader.pages):
                page_text += page.extract_text() + "\n"
            
            # Check if file mentions Xiaomi or ISIN
            if "KYG9830T1067" in page_text or "Xiaomi" in page_text:
                print(f"\n--- HIT in {pdf.name} ---")
                # Look for the target dates or quantities
                lines = page_text.split('\n')
                for i, line in enumerate(lines):
                    if any(t in line for t in targets):
                        # Print context
                        start = max(0, i-3)
                        end = min(len(lines), i+5)
                        print(f"[Line {i}] {line.strip()}")
                        for l in lines[start:end]:
                            if l.strip() != line.strip():
                                print(f"  {l.strip()}")
        except Exception as e:
            pass

if __name__ == "__main__":
    find_missing_movements()
