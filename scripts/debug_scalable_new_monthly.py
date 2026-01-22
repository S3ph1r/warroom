"""
Debug Scalable New Monthly Dump
Dump text from a new 'Monthly account statement Broker Scalable Capital' to check layout.
"""
from pathlib import Path
from pypdf import PdfReader

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def dump_new_monthly():
    # Find a "Monthly account statement Broker Scalable Capital"
    files = list(INBOX.glob("*Monthly account statement Broker Scalable Capital*.pdf"))
    if not files:
        print("No new monthly files found.")
        return
        
    target = files[0] # Pick one
    print(f"Analyzing: {target.name}")
    print("-" * 60)
    
    reader = PdfReader(target)
    for i, page in enumerate(reader.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
        print("-" * 20)

if __name__ == "__main__":
    dump_new_monthly()
