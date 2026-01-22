from pypdf import PdfReader
from pathlib import Path
import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

dir_path = Path(r"g:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
isin = "KYG9830T1067"

def analyze_xiaomi():
    print(f"Analyzing Xiaomi (ISIN: {isin}) across all PDFs...\n")
    pdf_files = list(dir_path.glob("*.pdf"))
    
    movements = []
    
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            page_text = ""
            for page in reader.pages:
                page_text += page.extract_text() + "\n"
            
            if isin in page_text or "Xiaomi" in page_text:
                # Look for lines around the ISIN or Name
                lines = page_text.split('\n')
                for i, line in enumerate(lines):
                    if isin in line or "Xiaomi" in line:
                        # Print context: 5 lines before and after
                        start = max(0, i - 5)
                        end = min(len(lines), i + 8)
                        context = "\n".join(lines[start:end])
                        movements.append({
                            "file": pdf.name,
                            "context": context
                        })
        except Exception as e:
            pass

    # Group by file and show
    for m in movements:
        print(f"FILE: {m['file']}")
        print("-" * 40)
        print(m['context'])
        print("=" * 60)

if __name__ == "__main__":
    analyze_xiaomi()
