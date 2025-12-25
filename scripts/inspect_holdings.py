
from db.database import SessionLocal
from db.models import Holding
from sqlalchemy import select

db = SessionLocal()
try:
    holdings = db.execute(select(Holding)).scalars().all()
    print(f"Total Holdings: {len(holdings)}")
    print(f"{'Ticker':<10} | {'Type':<15} | {'Value':<10}")
    print("-" * 40)
    for h in holdings:
        print(f"{h.ticker:<10} | {h.asset_type:<15} | {h.current_value:<10}")
finally:
    db.close()
