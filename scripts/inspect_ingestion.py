"""
Inspect IngestionBatch table.
"""
import sys
from pathlib import Path
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import IngestionBatch

def inspect_batches():
    session = SessionLocal()
    batches = session.scalars(select(IngestionBatch)).all()
    session.close()

    print(f"{'ID':<8} | {'Broker':<15} | {'File':<40} | {'Status':<10} | {'H':<3} | {'T':<3}")
    print("-" * 90)
    
    for b in batches:
        raw = b.raw_data or {}
        h_count = len(raw.get('holdings', []))
        t_count = len(raw.get('transactions', []))
        print(f"{str(b.id)[:8]} | {b.broker[:15]:<15} | {b.source_file[:40]:<40} | {b.status[:10]:<10} | {h_count:<3} | {t_count:<3}")

if __name__ == "__main__":
    inspect_batches()
