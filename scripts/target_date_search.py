from pypdf import PdfReader
from pathlib import Path
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def target_date_search():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    targets = ["27.12.2024", "30.12.2024", "27.12.24", "30.12.24"]
    
    print(f"Scanning {len(pdf_files)} files for Dec 2024 target dates...")
    
    for pdf in sorted(pdf_files):
        try:
            reader = PdfReader(pdf)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                for target in targets:
                    if target in text:
                        print(f"\n[FOUND] Date {target} in {pdf.name} (Page {i+1})")
                        # Show some context
                        lines = text.split('\n')
                        for line_idx, line in enumerate(lines):
                            if target in line:
                                start = max(0, line_idx - 3)
                                end = min(len(lines), line_idx + 10)
                                print("-" * 40)
                                for l in lines[start:end]:
                                    print(l.strip())
        except Exception as e:
            pass

if __name__ == "__main__":
    target_date_search()
