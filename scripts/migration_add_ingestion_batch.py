"""
Migration script to add 'ingestion_batches' table to the database.
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal

def run_migration():
    print("Running migration: Creating ingestion_batches table...")
    session = SessionLocal()
    try:
        # Check if table exists
        result = session.execute(text("SELECT to_regclass('public.ingestion_batches')"))
        if result.scalar():
            print("Table 'ingestion_batches' already exists.")
            return

        # Create table
        ddl = """
        CREATE TABLE ingestion_batches (
            id UUID PRIMARY KEY,
            broker VARCHAR(50) NOT NULL,
            source_file VARCHAR(255) NOT NULL,
            ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
            status VARCHAR(20) DEFAULT 'PENDING',
            raw_data JSON,
            validation_errors JSON,
            notes TEXT
        );
        """
        session.execute(text(ddl))
        session.commit()
        print("✅ Table 'ingestion_batches' created successfully.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
