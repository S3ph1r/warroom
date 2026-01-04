"""
Inventory Scalable Inbox
Lists all files in the Scalable inbox, categorizing them and analyzing unknown types.
"""
from pathlib import Path
from pypdf import PdfReader
import collections

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def analyze_inbox():
    print("=" * 60)
    print("📂 SCALABLE INBOX INVENTORY")
    print("=" * 60)
    
    all_files = list(INBOX.glob("*.pdf"))
    all_files.sort(key=lambda x: x.name)
    
    monthly = []
    others = []
    
    for p in all_files:
        if "Monthly account statement Baader Bank" in p.name:
            monthly.append(p)
        else:
            others.append(p)
            
    print(f"Total PDFs: {len(all_files)}")
    print(f"Monthly Statements: {len(monthly)}")
    print(f"Other Documents: {len(others)}")
    
    # 1. Analyze Monthly Coverage (Briefly)
    if monthly:
        print("\n📅 Monthly Statements Coverage:")
        print(f"   First: {monthly[0].name}")
        print(f"   Last:  {monthly[-1].name}")
    
    # 2. Analyze Others - Group by Pattern
    if others:
        print("\n📄 ANALYSIS OF OTHER DOCUMENTS:")
        print("-" * 60)
        
        patterns = collections.defaultdict(list)
        for p in others:
            # Mask digits to find pattern
            clean_name = ''.join(['#' if c.isdigit() else c for c in p.name])
            # Trim date prefix if present (######## ...)
            if clean_name.startswith("########"):
                clean_name = clean_name[8:].strip()
            patterns[clean_name].append(p)
            
        for pat, files in patterns.items():
            print(f"🔹 PATTERN: {pat} ({len(files)} files)")
            # Peek at first one
            try:
                reader = PdfReader(files[0])
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text().split('\n')
                    print(f"   📝 Header: {text[0].strip()} / {text[1].strip() if len(text)>1 else ''}")
            except:
                pass
            print("-" * 20)
    else:
        print("\n✅ No other documents found (Only Monthly Statements present).")

if __name__ == "__main__":
    analyze_inbox()
