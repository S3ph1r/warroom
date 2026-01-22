
from db.database import SessionLocal
from db.models import PortfolioSnapshot
from datetime import date, timedelta
from sqlalchemy import select
import random

def seed_history():
    db = SessionLocal()
    try:
        # Check current snapshots
        snaps = db.execute(select(PortfolioSnapshot)).scalars().all()
        print(f"Current snapshots: {len(snaps)}")
        
        if len(snaps) >= 2:
            print("Enough history exists.")
            return

        today = date.today()
        # Create 5 days of fake history
        base_value = 32000.0
        
        for i in range(5, 0, -1):
            d = today - timedelta(days=i)
            # Check if exists
            exists = db.execute(select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == d)).scalar_one_or_none()
            if exists: continue
            
            # Random variation
            val = base_value * (1 + (random.random() * 0.05 - 0.02))
            
            snap = PortfolioSnapshot(
                snapshot_date=d,
                total_value=val,
                total_cost=35000.0,
                pnl_net=val - 35000,
                pnl_pct=((val - 35000)/35000)*100,
                broker_breakdown={},
                asset_breakdown={},
                holdings_count=10
            )
            db.add(snap)
            print(f"Added snapshot for {d}: {val:.2f}")
            
        db.commit()
        print("Seeding complete.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_history()
