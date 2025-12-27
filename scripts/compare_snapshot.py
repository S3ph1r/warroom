
import json
import sys
import os
from pathlib import Path
from decimal import Decimal
from sqlalchemy import text, create_engine

# Setup Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from db.database import engine

SNAPSHOT_FILE = "scripts/db_snapshot_pre_ingest.json"
REPORT_FILE = "scripts/ingestion_comparison_report.txt"

def load_old_holdings():
    if not Path(SNAPSHOT_FILE).exists():
        return {}
    with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Map (Broker, Ticker) -> Qty
    holdings = {}
    for item in data:
        key = (item.get("broker"), item.get("asset")) # 'asset' was used for ticker
        qty = float(item.get("quantity", 0))
        holdings[key] = qty
    return holdings

def load_new_holdings():
    holdings = {}
    with engine.connect() as conn:
        result = conn.execute(text("SELECT broker, ticker, quantity FROM holdings"))
        for r in result:
            key = (r[0], r[1])
            qty = float(r[2])
            holdings[key] = qty
    return holdings

def compare():
    print("Generating Comparison Report...")
    old = load_old_holdings()
    new = load_new_holdings()
    
    all_keys = set(old.keys()) | set(new.keys())
    
    added = []
    removed = []
    changed = []
    same = []
    
    for k in all_keys:
        old_q = old.get(k, 0.0)
        new_q = new.get(k, 0.0)
        
        diff = new_q - old_q
        
        if k not in old:
            added.append((k, new_q))
        elif k not in new:
            removed.append((k, old_q))
        elif abs(diff) > 0.0001:
            changed.append((k, old_q, new_q, diff))
        else:
            same.append((k, new_q))

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("=== INGESTION COMPARISON REPORT ===\n")
        f.write(f"Old Holdings Count: {len(old)}\n")
        f.write(f"New Holdings Count: {len(new)}\n\n")
        
        if added:
            f.write(f"--- ADDED ({len(added)}) ---\n")
            for k, q in sorted(added):
                f.write(f"  [+] {k[0]} | {k[1]}: {q}\n")
            f.write("\n")
            
        if removed:
            f.write(f"--- REMOVED ({len(removed)}) ---\n")
            for k, q in sorted(removed):
                f.write(f"  [-] {k[0]} | {k[1]}: {q}\n")
            f.write("\n")
            
        if changed:
            f.write(f"--- CHANGED ({len(changed)}) ---\n")
            for k, o, n, d in sorted(changed):
                f.write(f"  [*] {k[0]} | {k[1]}: Old={o} -> New={n} (Diff: {d:+.4f})\n")
            f.write("\n")
            
        f.write(f"--- UNCHANGED ({len(same)}) ---\n")
        f.write(f"  (Listing first 10)\n")
        for k, q in sorted(same)[:10]:
             f.write(f"  [=] {k[0]} | {k[1]}: {q}\n")

    print(f"Report generated: {REPORT_FILE}")
    print(f"Stats: Added {len(added)}, Removed {len(removed)}, Changed {len(changed)}, Same {len(same)}")

if __name__ == "__main__":
    compare()
