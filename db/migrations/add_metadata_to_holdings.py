"""
Migration: Add asset metadata fields to HOLDINGS table
Adds share_class, adr_ratio, nominal_value, market to Holding table.

Run: python db/migrations/add_metadata_to_holdings.py
"""
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from db.database import engine

def upgrade():
    """Add metadata columns to holdings table"""
    print("🔄 Adding asset metadata fields to holdings table...")
    
    with engine.connect() as conn:
        columns = [
            ("share_class", "VARCHAR(10)"),
            ("adr_ratio", "FLOAT"),
            ("nominal_value", "VARCHAR(20)"),
            ("market", "VARCHAR(10)")
        ]
        
        for col_name, col_type in columns:
            try:
                # SQLite doesn't support IF NOT EXISTS in ADD COLUMN directly in standard SQL standard but often works
                # Safer to just try and match error
                conn.execute(text(f"ALTER TABLE holdings ADD COLUMN {col_name} {col_type}"))
                print(f"  + Added {col_name}")
            except Exception as e:
                # Check directly if it's a duplicate column error
                if "duplicate column name" in str(e).lower():
                    print(f"  = Column {col_name} already exists")
                else:
                    print(f"  ! Error adding {col_name}: {e}")
        
        conn.commit()
        print("✅ Migration completed: Added asset metadata fields to holdings")

def downgrade():
    """Remove metadata columns from holdings table"""
    print("🔄 Removing asset metadata fields from holdings table...")
    
    with engine.connect() as conn:
        for col in ["share_class", "adr_ratio", "nominal_value", "market"]:
            try:
                conn.execute(text(f"ALTER TABLE holdings DROP COLUMN {col}"))
                print(f"  - Removed {col}")
            except Exception as e:
                print(f"  ! Error removing {col}: {e}")
        
        conn.commit()
        print("✅ Migration rolled back: Removed asset metadata fields from holdings")

if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add project root to path
    root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(root))
    
    upgrade()
