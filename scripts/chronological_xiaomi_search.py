import re
from pathlib import Path
from pypdf import PdfReader
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def find_first_xiaomi():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    # Identify Monthly Statements and Fiscal Reports
    candidates = list(dir_path.glob("*Monthly account statement*.pdf")) + \
                 list(dir_path.glob("*Report fiscale*.pdf")) + \
                 list(dir_path.glob("*Account statement*.pdf"))
    
    # Sort by filename (prefix is YYYYMMDD)
    candidates.sort(key=lambda x: x.name)
    
    isin = "KYG9830T1067"
    print(f"Searching for {isin} (Xiaomi) chronologically...\n")
    
    for pdf in candidates:
        try:
            reader = PdfReader(pdf)
            found_in_file = False
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if isin in text or "Xiaomi" in text:
                    if not found_in_file:
                        print(f"\n>>> {pdf.name}")
                        found_in_file = True
                    
                    lines = text.split('\n')
                    for line_idx, line in enumerate(lines):
                        if isin in line or "Xiaomi" in line:
                            # Print context
                            start = max(0, line_idx - 2)
                            end = min(len(lines), line_idx + 5)
                            print(f"  [Page {i+1}]")
                            for l in lines[start:end]:
                                print(f"    {l.strip()}")
        except Exception as e:
            # print(f"Error reading {pdf.name}: {e}")
            pass

if __name__ == "__main__":
    find_first_xiaomi()
