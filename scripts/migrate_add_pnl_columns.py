"""
Migration: Add realized_pnl and fx_cost columns to transactions table
Date: 2026-01-03
"""
from db.database import engine
from sqlalchemy import text

def run_migration():
    print("🔄 Running migration: Add realized_pnl and fx_cost to transactions...")
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'transactions' AND column_name IN ('realized_pnl', 'fx_cost')
        """))
        existing = [r[0] for r in result.fetchall()]
        
        if 'realized_pnl' not in existing:
            print("   Adding realized_pnl column...")
            conn.execute(text("ALTER TABLE transactions ADD COLUMN realized_pnl DECIMAL(18,2)"))
        else:
            print("   realized_pnl already exists")
            
        if 'fx_cost' not in existing:
            print("   Adding fx_cost column...")
            conn.execute(text("ALTER TABLE transactions ADD COLUMN fx_cost DECIMAL(18,2)"))
        else:
            print("   fx_cost already exists")
            
        conn.commit()
        
    print("✅ Migration complete!")

if __name__ == "__main__":
    run_migration()
