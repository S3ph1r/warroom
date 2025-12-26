
import sys
import os
from sqlalchemy import text

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        print("Migrating: Adding 'status' column to transactions table...")
        # Check if column exists first (postgres specific check, or just try/except)
        try:
            db.execute(text("ALTER TABLE transactions ADD COLUMN status VARCHAR(20) DEFAULT 'COMPLETED'"))
            db.commit()
            print("✅ Migration successful: Column 'status' added.")
        except Exception as e:
            print(f"⚠️ Migration note (might already exist): {e}")
            db.rollback()
            
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
