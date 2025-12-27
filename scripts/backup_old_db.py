
import json
import sys
import os
from pathlib import Path
from sqlalchemy import text

# Setup Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Engine
try:
    from db.database import engine
    print("Successfully imported engine from db.database")
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

OUTPUT_FILE = "scripts/db_snapshot_pre_ingest.json"

def backup():
    print("Backing up Old DB Holdings...")
    try:
        with engine.connect() as conn:
            # Query Holdings
            # Table name is 'holdings' (from models.py)
            # Columns: broker, ticker, isin, name, quantity
            result = conn.execute(text("SELECT ticker, name, isin, quantity, broker FROM holdings"))
            
            rows = []
            for r in result:
                rows.append({
                    "asset": r[0], # Ticker
                    "name": r[1],
                    "isin": r[2],
                    "quantity": float(r[3]) if r[3] is not None else 0.0,
                    "broker": r[4]
                })
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(rows, f, indent=2)
                
            print(f"Snapshot saved: {len(rows)} entries to {OUTPUT_FILE}")
            return True
            
    except Exception as e:
        print(f"Backup Failed: {e}")
        # Save empty
        with open(OUTPUT_FILE, 'w') as f:
            json.dump([], f)
        return False

if __name__ == "__main__":
    backup()
