"""
Debug Scalable Native Dump
Dump text from a new 'Scalable Capital' branded statement to check format compatibility.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def dump_native():
    # Find the specific file
    files = list(INBOX.glob("*Securities account statement Broker Scalable Capital*.pdf"))
    if not files:
        print("No native files found.")
        return
        
    target = files[-1] # Newest
    print(f"Analyzing: {target.name}")
    print("-" * 60)
    
    reader = PdfReader(target)
    for i, page in enumerate(reader.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
        print("-" * 20)

if __name__ == "__main__":
    dump_native()
