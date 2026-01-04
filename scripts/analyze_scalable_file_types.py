"""
Analyze All Scalable File Types
Identify which file types contain transactions and should be processed.
"""
from pathlib import Path
from pypdf import PdfReader
from collections import defaultdict
import re

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def analyze_file_types():
    print("=" * 60)
    print("📂 SCALABLE FILE TYPE ANALYSIS")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    
    # Group by type (remove date and hash)
    type_groups = defaultdict(list)
    
    for p in files:
        # Extract type by removing YYYYMMDD prefix and hash suffix
        name = p.name
        # Remove date
        name_no_date = re.sub(r'^\d{8}\s+', '', name)
        # Remove hash (last word before .pdf if it's 6 chars alphanumeric)
        parts = name_no_date.replace('.pdf', '').rsplit(' ', 1)
        if len(parts) == 2 and len(parts[1]) == 6 and any(c.isdigit() for c in parts[1]):
            file_type = parts[0]
        else:
            file_type = name_no_date.replace('.pdf', '')
            
        type_groups[file_type].append(p)
    
    # Analyze each type
    for file_type, file_list in sorted(type_groups.items()):
        print(f"\n📁 TYPE: '{file_type}' ({len(file_list)} files)")
        
        # Sample first file
        sample = file_list[0]
        print(f"   Sample: {sample.name}")
        
        # Check for transaction keywords
        try:
            reader = PdfReader(sample)
            text = ""
            for page in reader.pages[:3]:  # First 3 pages
                text += page.extract_text()
            
            has_purchase = "Purchase" in text or "Acquisto" in text
            has_sale = "Sale" in text or "Vendita" in text
            has_isin = "ISIN" in text and "US" in text  # ISIN pattern
            has_stk = "STK" in text
            
            if has_purchase or has_sale:
                print(f"   ✅ CONTAINS TRANSACTIONS")
                print(f"      Purchase: {has_purchase}, Sale: {has_sale}")
                print(f"      ISIN: {has_isin}, STK: {has_stk}")
            else:
                print(f"   ℹ️  No obvious transactions")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_file_types()
