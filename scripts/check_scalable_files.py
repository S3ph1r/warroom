"""
Check Scalable Files Coverage
Lists all Scalable/Baader PDFs, determines the date range, and checks for missing months.
"""
from pathlib import Path
import re
from datetime import datetime, timedelta

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def check_files():
    print("=" * 60)
    print("📂 SCALABLE FILE COVERAGE CHECK")
    print("=" * 60)
    
    files = list(INBOX.glob("*Monthly account statement Baader Bank*.pdf"))
    files.sort(key=lambda x: x.name)
    
    if not files:
        print("❌ No files found!")
        return

    print(f"Found {len(files)} files.")
    
    # Parse Dates
    dates = []
    for p in files:
        # Expected: YYYYMMDD ...
        match = re.match(r'^(\d{8})', p.name)
        if match:
            d_str = match.group(1)
            try:
                d = datetime.strptime(d_str, "%Y%m%d")
                dates.append(d)
                # print(f"  - {d.strftime('%Y-%m-%d')} ({p.name})")
            except:
                print(f"  ⚠️ Invalid date format in: {p.name}")
        else:
            print(f"  ⚠️ No date found in: {p.name}")
            
    if not dates:
        print("❌ No valid dates extracted.")
        return
        
    dates.sort()
    min_date = dates[0]
    max_date = dates[-1]
    
    print("-" * 60)
    print(f"🗓️  Start Date (File): {min_date.strftime('%Y-%m-%d')}")
    print(f"🗓️  End Date (File):   {max_date.strftime('%Y-%m-%d')}")
    
    # Check for Gaps
    # We expect roughly 1 file per month. The file date is usually early next month (e.g. 20240806 for July).
    # Let's check YYYY-MM coverage.
    
    found_months = set((d.year, d.month) for d in dates)
    
    # Generate expected months from min to max
    curr = min_date.replace(day=1)
    end = max_date.replace(day=1)
    
    missing = []
    while curr <= end:
        if (curr.year, curr.month) not in found_months:
            missing.append(curr.strftime("%Y-%m"))
        # Increment month
        if curr.month == 12:
            curr = curr.replace(year=curr.year+1, month=1)
        else:
            curr = curr.replace(month=curr.month+1)
            
    print("-" * 60)
    if missing:
        print(f"❌ POTENTIAL MISSING MONTHS (based on file dates):")
        for m in missing:
            print(f"  - {m}")
    else:
        print("✅ No date gaps found in file sequence.")
        
    # Also Check for overlapping months (duplicates)
    file_map = {}
    for p in files:
         match = re.match(r'^(\d{6})', p.name)
         if match:
             ym = match.group(1)
             if ym not in file_map: file_map[ym] = []
             file_map[ym].append(p.name)
             
    duplicates = {k: v for k, v in file_map.items() if len(v) > 1}
    if duplicates:
        print("-" * 60)
        print("⚠️ DUPLICATE MONTHS DETECTED (Multiple files for same YYYYMM):")
        for k, v in duplicates.items():
            print(f"  - {k}: {v}")
    
if __name__ == "__main__":
    check_files()
