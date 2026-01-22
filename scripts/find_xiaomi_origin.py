from pypdf import PdfReader
from pathlib import Path
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def find_xiaomi_origin():
    dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    isin = "KYG9830T1067"
    wkn = "A2JNY1"
    
    print(f"Searching for {isin} / {wkn} / Xiaomi across {len(pdf_files)} files...")
    
    results = []
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            found = False
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if isin in text or wkn in text or "Xiaomi" in text:
                    if not found:
                        results.append(pdf.name)
                        found = True
                    # Print context if it's an old file
                    if "2022" in pdf.name or "2023" in pdf.name:
                        print(f"\n>>> FOUND in {pdf.name} (Page {i+1})")
                        lines = text.split('\n')
                        for line in lines:
                            if isin in line or wkn in line or "Xiaomi" in line:
                                print(f"  {line.strip()}")
        except Exception as e:
            pass

    print("\nSummary of files with Xiaomi:")
    for res in sorted(results):
        print(f" - {res}")

if __name__ == "__main__":
    find_xiaomi_origin()
