"""
Cleanup script for Scalable Capital Test.
Wipes DB entries for Scalable and deletes temporary orchestration/extraction files.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, Holding

def cleanup():
    print("🧹 Starting cleanup for Scalable Capital test...")
    session = SessionLocal()
    
    # 1. Clean DB
    print("   🗑️ Deleting Scalable Transactions from DB...")
    tx_deleted = session.query(Transaction).filter(Transaction.broker == "SCALABLE").delete()
    print(f"      Deleted {tx_deleted} transactions.")
    
    print("   🗑️ Deleting Scalable Holdings from DB...")
    hold_deleted = session.query(Holding).filter(Holding.broker == "SCALABLE").delete()
    print(f"      Deleted {hold_deleted} holdings.")
    
    session.commit()
    session.close()
    
    # 2. Delete Temp Files
    files_to_delete = [
        project_root / "orchestration_results.json",
        project_root / "extraction_results.json",
        project_root / "data" / "portfolio_snapshot.json",
        project_root / "warroom_ingestion.log" # Clear old log
    ]
    
    for f in files_to_delete:
        if f.exists():
            print(f"   🗑️ Deleting {f.name}...")
            f.unlink()
        else:
            print(f"   ℹ️ {f.name} not found, skipping.")
            
    print("✨ Cleanup complete. Fresh state ready.")

if __name__ == "__main__":
    cleanup()
