"""
Debug Scalable Specific File
Dump text from a specific Scalable/Baader file to check for unparsed operations.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
FILENAME = "20240809 Monthly account statement Baader Bank 9CzG19.pdf"

def dump_file():
    target = INBOX / FILENAME
    if not target.exists():
        # Try finding by partial name
        candidates = list(INBOX.glob("*20240809*.pdf"))
        if candidates:
            target = candidates[0]
        else:
            print("File not found.")
            return

    print(f"Analyzing: {target.name}")
    print("-" * 60)
    
    reader = PdfReader(target)
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        full_text += text
        print(f"--- PAGE {i+1} ---")
        print(text)
        print("-" * 20)
        
    print("\n🔎 TESLA CONTEXT:")
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        if "Tesla" in line or "US88160R1014" in line:
            # Print context
            start = max(0, i-5)
            end = min(len(lines), i+5)
            print("\n".join(lines[start:end]))
            print("..." + "-"*20 + "...")

if __name__ == "__main__":
    dump_file()
