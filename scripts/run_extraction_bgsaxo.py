import sys
from pathlib import Path

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.universal_ingestion_router import process_csv_direct

# G: drive path
csv_path = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv")

if not csv_path.exists():
    print(f"❌ File not found: {csv_path}")
    sys.exit(1)

print(f"🚀 Starting Extraction for: {csv_path}")
out = process_csv_direct(csv_path)

if out:
    print(f"✅ Extraction Complex. Output: {out}")
else:
    print("❌ Extraction Failed.")
