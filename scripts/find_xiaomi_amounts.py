from pypdf import PdfReader
from pathlib import Path
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def find_xiaomi_amounts():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    # Amounts from Fiscal Report (likely Purchase Value or Market Value)
    # 170,50 or 170.50
    # 255,72 or 255.72
    targets = ["170,50", "170.50", "255,72", "255.72"]
    
    print(f"Scanning {len(pdf_files)} files for amounts {targets}...")
    
    for pdf in sorted(pdf_files):
        try:
            reader = PdfReader(pdf)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                for t in targets:
                    if t in text:
                        print(f"\n[HIT] Found '{t}' in {pdf.name} (Page {i+1})")
                        lines = text.split('\n')
                        for idx, line in enumerate(lines):
                            if t in line:
                                print(f"  > {line.strip()}")
        except Exception as e:
            pass

if __name__ == "__main__":
    find_xiaomi_amounts()
