"""
Migration: Add asset metadata fields to transactions table
Adds share_class, adr_ratio, nominal_value, market to Transaction table only.

Run: python db/migrations/add_asset_metadata.py
"""
from sqlalchemy import text
from db.database import engine

def upgrade():
    """Add metadata columns to transactions table"""
    print("🔄 Adding asset metadata fields to transactions table...")
    
    with engine.connect() as conn:
        # Add columns to transactions table ONLY
        conn.execute(text("ALTER TABLE transactions ADD COLUMN share_class VARCHAR(10)"))
        conn.execute(text("ALTER TABLE transactions ADD COLUMN adr_ratio FLOAT"))
        conn.execute(text("ALTER TABLE transactions ADD COLUMN nominal_value VARCHAR(20)"))
        conn.execute(text("ALTER TABLE transactions ADD COLUMN market VARCHAR(10)"))
        
        conn.commit()
        print("✅ Migration completed: Added asset metadata fields to transactions")

def downgrade():
    """Remove metadata columns from transactions table"""
    print("🔄 Removing asset metadata fields from transactions table...")
    
    with engine.connect() as conn:
        # Remove from transactions
        conn.execute(text("ALTER TABLE transactions DROP COLUMN share_class"))
        conn.execute(text("ALTER TABLE transactions DROP COLUMN adr_ratio"))
        conn.execute(text("ALTER TABLE transactions DROP COLUMN nominal_value"))
        conn.execute(text("ALTER TABLE transactions DROP COLUMN market"))
        
        conn.commit()
        print("✅ Migration rolled back: Removed asset metadata fields from transactions")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit('\\', 3)[0])  # Add project root to path
    
    upgrade()
