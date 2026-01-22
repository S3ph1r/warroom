
import sys
import os
from pathlib import Path
from sqlalchemy import select, func

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import PortfolioSnapshot

def check_snapshots():
    db = SessionLocal()
    try:
        count = db.execute(select(func.count(PortfolioSnapshot.id))).scalar()
        print(f"Total Snapshots: {count}")
        
        snapshots = db.execute(select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date)).scalars().all()
        for s in snapshots:
            print(f"  {s.snapshot_date}: Val={s.total_value}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_snapshots()
