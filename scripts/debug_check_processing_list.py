"""
Debug Check Processing List
Verify which files are being processed by the ingestion script.
"""
import re
from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

def check_list():
    baader_files = list(INBOX.glob("*Monthly account statement Baader Bank*.pdf"))
    scalable_files = list(INBOX.glob("*Monthly account statement Broker Scalable Capital*.pdf"))
    
    all_raw_files = baader_files + scalable_files
    print(f"Total Files: {len(all_raw_files)} (Baader: {len(baader_files)}, Scalable: {len(scalable_files)})")
    
    file_map = {}
    
    for p in all_raw_files:
        match = re.match(r'^(\d{6})\d{2}', p.name)
        if match:
            yyyymm = match.group(1)
            
            if yyyymm not in file_map:
                file_map[yyyymm] = p
            else:
                current_p = file_map[yyyymm]
                curr_is_baader = "Baader Bank" in current_p.name
                new_is_baader = "Baader Bank" in p.name
                
                if new_is_baader and not curr_is_baader:
                    file_map[yyyymm] = p
                elif new_is_baader and curr_is_baader:
                    if p.name > current_p.name:
                        file_map[yyyymm] = p
                elif not new_is_baader and not curr_is_baader:
                    if p.name > current_p.name:
                        file_map[yyyymm] = p
                        
    final_list = sorted(file_map.values(), key=lambda x: x.name)
    
    print(f"\nFinal Processing List ({len(final_list)} files):")
    # Show only late 2024 / 2025 files
    for f in final_list:
        if f.name.startswith("20241") or f.name.startswith("2025") or f.name.startswith("2026"):
            print(f"  - {f.name}")
        
    # Check for December 2024
    dec2024 = [f for f in final_list if f.name.startswith("202412")]
    print(f"\n🔍 December 2024 files: {dec2024}")

if __name__ == "__main__":
    check_list()
