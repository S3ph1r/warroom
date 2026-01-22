"""
Refresh Dashboard Data
Deletes the 'portfolio_snapshot.json' to force the dashboard to rebuild data from the database.
"""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent
SNAPSHOT_PATH = PROJECT_ROOT / "data" / "portfolio_snapshot.json"

def refresh_dashboard():
    print("=" * 60)
    print("🔄 REFRESHING DASHBOARD DATA")
    print("=" * 60)
    
    if SNAPSHOT_PATH.exists():
        try:
            os.remove(SNAPSHOT_PATH)
            print(f"✅ Deleted snapshot: {SNAPSHOT_PATH.name}")
            print("   The dashboard will regenerate clean data on the next page load.")
        except Exception as e:
            print(f"❌ Error deleting snapshot: {e}")
    else:
        print("ℹ️ Snapshot not found (Data is already fresh or not generated).")
        
if __name__ == "__main__":
    refresh_dashboard()
