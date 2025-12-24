import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.database import engine

def migrate():
    print("Running migration v4: Adding multi-currency columns to holdings table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS native_current_value DECIMAL(18, 2)"))
            conn.execute(text("ALTER TABLE holdings ADD COLUMN IF NOT EXISTS exchange_rate_used DECIMAL(18, 6)"))
            conn.commit()
            print("✅ Migration complete: Added columns to holdings table.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate()
