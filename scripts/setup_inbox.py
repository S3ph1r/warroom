"""
WAR ROOM - Setup Inbox Structure on Google Drive
Run this script ONCE to create the folder structure for data ingestion
"""
import os
from pathlib import Path

# Google Drive root path - ADJUST IF NEEDED
DRIVE_ROOT = "G:\\Il mio Drive"  # Italian
# DRIVE_ROOT = "G:\\My Drive"  # English

# Folder structure
FOLDERS = [
    "WAR_ROOM_DATA/inbox/bgsaxo",
    "WAR_ROOM_DATA/inbox/scalable",
    "WAR_ROOM_DATA/inbox/binance",
    "WAR_ROOM_DATA/inbox/coinbase",
    "WAR_ROOM_DATA/inbox/traderepublic",
    "WAR_ROOM_DATA/inbox/ibkr",
    "WAR_ROOM_DATA/inbox/fineco",
    "WAR_ROOM_DATA/inbox/revolut",
    "WAR_ROOM_DATA/inbox/cryptocom",
    "WAR_ROOM_DATA/processed/bgsaxo",
    "WAR_ROOM_DATA/processed/scalable",
    "WAR_ROOM_DATA/processed/binance",
    "WAR_ROOM_DATA/processed/coinbase",
    "WAR_ROOM_DATA/processed/traderepublic",
    "WAR_ROOM_DATA/processed/ibkr",
    "WAR_ROOM_DATA/processed/fineco",
    "WAR_ROOM_DATA/processed/revolut",
    "WAR_ROOM_DATA/processed/cryptocom",
    "WAR_ROOM_DATA/logs",
]


def main():
    print("🚀 WAR ROOM - Setup Inbox Structure")
    print("=" * 50)
    
    # Check if Drive is accessible
    if not os.path.exists(DRIVE_ROOT):
        print(f"❌ Google Drive not found at: {DRIVE_ROOT}")
        print("\n💡 Try adjusting DRIVE_ROOT in this script:")
        print("   - Italian: G:\\Il mio Drive")
        print("   - English: G:\\My Drive")
        return False
    
    print(f"✅ Google Drive found at: {DRIVE_ROOT}")
    
    # Create folders
    created = 0
    for folder in FOLDERS:
        folder_path = Path(DRIVE_ROOT) / folder
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created: {folder}")
            created += 1
        else:
            print(f"  ✓ Exists: {folder}")
    
    print("=" * 50)
    print(f"✅ Setup complete! Created {created} new folders.")
    print(f"\n📂 Your inbox is at: {DRIVE_ROOT}\\WAR_ROOM_DATA\\inbox")
    
    # Return the root path for .env configuration
    war_room_path = Path(DRIVE_ROOT) / "WAR_ROOM_DATA"
    print(f"\n📋 Add this to your .env file:")
    print(f'INBOX_ROOT_PATH={war_room_path / "inbox"}')
    print(f'PROCESSED_ROOT_PATH={war_room_path / "processed"}')
    
    return True


if __name__ == "__main__":
    main()
