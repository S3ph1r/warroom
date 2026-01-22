"""
WAR ROOM - Move existing broker files to Google Drive structure
Run this script ONCE to move already processed files to the new structure
"""
import shutil
from pathlib import Path

# Source locations (local)
SOURCES = {
    "bgsaxo": Path("D:/Download/BGSAXO"),
    "scalable": Path("D:/Download/SCALABLE CAPITAL"),
}

# Google Drive processed folder
DRIVE_PROCESSED = Path("G:/Il mio Drive/WAR_ROOM_DATA/processed")


def main():
    print("📦 WAR ROOM - Move Files to Google Drive")
    print("=" * 50)
    
    for broker, source_path in SOURCES.items():
        if not source_path.exists():
            print(f"⚠️ {broker}: Source not found at {source_path}")
            continue
        
        dest_path = DRIVE_PROCESSED / broker
        if not dest_path.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
        
        files = list(source_path.glob("*.*"))
        print(f"\n📁 {broker.upper()}: {len(files)} files")
        
        for f in files:
            dest_file = dest_path / f.name
            if not dest_file.exists():
                shutil.copy2(f, dest_file)
                print(f"  ✓ Copied: {f.name}")
            else:
                print(f"  - Exists: {f.name}")
    
    print("\n" + "=" * 50)
    print("✅ Files copied to Google Drive!")
    print("\n💡 Original files left in place (you can delete them manually if you want)")


if __name__ == "__main__":
    main()
