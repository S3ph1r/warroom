import sys
import codecs
from pypdf import PdfReader
from pathlib import Path

# Force UTF-8 for Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def dump_text(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: File not found {pdf_path}")
        return

    try:
        reader = PdfReader(path)
        print(f"--- DUMPING: {path.name} ({len(reader.pages)} pages) ---")
        for i, page in enumerate(reader.pages):
            print(f"\n--- PAGE {i+1} ---")
            print(page.extract_text())
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dump_pdf_text.py <path_to_pdf>")
    else:
        dump_text(sys.argv[1])
