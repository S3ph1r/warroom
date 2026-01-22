"""
Analyze Scalable Dump
Groups PDF files by title pattern, checks content, and identifies useful vs useless files.
"""
from pathlib import Path
import re
from collections import defaultdict
from pypdf import PdfReader
from datetime import datetime

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def parse_filename(filename):
    # Pattern: YYYYMMDD <Title> <Hash>.pdf
    # or: YYYYMMDD <Title>.pdf
    
    # 1. Extract Date
    date_part = filename[:8]
    if not date_part.isdigit():
        return None, filename, None
        
    rest = filename[9:-4] # Remove Date and .pdf
    
    # 2. Extract Hash (Last word if roughly 6 chars alphanumeric)
    parts = rest.rsplit(' ', 1)
    if len(parts) == 2 and len(parts[1]) == 6 and any(c.isdigit() for c in parts[1]):
        title = parts[0]
        file_hash = parts[1]
    else:
        title = rest
        file_hash = None
        
    return date_part, title, file_hash

def analyze_dump():
    print("=" * 60)
    print("🧐 SCALABLE DUMP ANALYSIS")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    files.sort(key=lambda x: x.name)
    
    groups = defaultdict(list)
    
    for p in files:
        d, title, h = parse_filename(p.name)
        groups[title].append(p)
        
    # Analysis
    useful_groups = []
    useless_files = []
    
    print(f"Found {len(files)} files in {len(groups)} groups.\n")
    
    for title, file_list in groups.items():
        count = len(file_list)
        first_file = file_list[0]
        last_file = file_list[-1]
        
        print(f"📁 GROUP: '{title}' ({count} files)")
        print(f"   First: {first_file.name}")
        
        # Check Content (Sample first file)
        is_useful = False
        sample_text = ""
        try:
            reader = PdfReader(first_file)
            if len(reader.pages) > 0:
                sample_text = reader.pages[0].extract_text()
        except:
            sample_text = "Error reading PDF"
            
        # Determine Usefulness
        if "Monthly account statement" in title:
            print("   ✅ STATUS: USEFUL (Transaction History)")
            is_useful = True
            useful_groups.append(title)
        elif "Securities account statement" in title:
            # Check if it has transactions or just holdings
            if "Transazioni" in sample_text or "Transactions" in sample_text:
                 print("   ❓ STATUS: CHECK (Might have transactions)")
                 is_useful = True
            else:
                 print("   ℹ️ STATUS: SNAPSHOT (Holdings only)")
                 is_useful = True # Still useful for cross check
        elif "Statement of accounts" in title:
             print("   INFO: Quarterly? Check if redundant.")
        elif "Corporate actions" in title:
             print("   ✅ STATUS: USEFUL (Dividends/Splits)")
             is_useful = True
        elif "Information" in title or "Privacy" in title or "Contract" in title or "Termini" in title or "Mandato" in title:
             print("   🗑️ STATUS: USELESS (Legal/Info)")
             useless_files.extend(file_list)
        else:
             print("   ❓ STATUS: UNKNOWN")
             
        print("-" * 40)

    # Coverage Analysis (Monthly Statements)
    print("\n📅 HISTORY COVERAGE (Monthly Statements):")
    monthly_files = []
    for title in useful_groups:
        if "Monthly" in title:
            monthly_files.extend(groups[title])
            
    if monthly_files:
        monthly_files.sort(key=lambda x: x.name)
        dates = [f.name[:8] for f in monthly_files]
        print(f"   Start: {dates[0]}")
        print(f"   End:   {dates[-1]}")
        
        # Check gaps
        # ... (Simplified for this script)
    
    print("\n🗑️ FILES TO DELETE (Proposal):")
    print(f"   Found {len(useless_files)} files to remove.")
    # for f in useless_files:
    #    print(f"   - {f.name}")

if __name__ == "__main__":
    analyze_dump()
