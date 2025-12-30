"""
Test Full Automation
Orchestrates the complete ingestion loop for BG SAXO:
1. Reset DB (Delete all 'bgsaxo' data)
2. Load Holdings (from High-Quality JSON)
3. Load Transactions (from Extracted CSV)
4. Reconcile
"""
import sys
import os
import json
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from decimal import Decimal

# Setup Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.load_universal_transactions_standalone import load_data as load_transactions
from scripts.reconcile_history import reconcile
from db.database import SessionLocal
from db.models import Holding

# High-Quality Data Source
# Note: Using the file in 'bgsaxo/' folder because it contains ISINs required for mapping,
# whereas the root extracted one has richer price data but missing ISINs.
HOLDINGS_PATH = ROOT_DIR / "data/extracted/bgsaxo/Posizioni_19-dic-2025_17_49_12.csv.json"
TRANSACTIONS_PATH = ROOT_DIR / "data/extracted/BG_SAXO_Transactions_FinalVersion.csv"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Automation")

def get_db_url():
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / '.env')
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "warroom")
    return f"postgresql://{user}:{password}@{server}:{port}/{db}"

def reset_db_broker(broker="bgsaxo"):
    logger.info(f"🧨 RESETTING DB for broker: {broker}...")
    engine = create_engine(get_db_url())
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM transactions WHERE broker = '{broker}'"))
        conn.execute(text(f"DELETE FROM holdings WHERE broker = '{broker}'"))
    logger.info("   ✅ Cleaned.")

def load_holdings_hq():
    logger.info(f"💼 LOADING HOLDINGS from {HOLDINGS_PATH.name}...")
    if not HOLDINGS_PATH.exists():
        logger.error("   ❌ File not found!")
        return
        
    with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    items = data.get('data', [])
    if not items and isinstance(data, list): items = data
    
    db = SessionLocal()
    try:
        count = 0
        for item in items:
            ticker = item.get('ticker') or item.get('symbol')
            # Fallback for symbol
            name = item.get('name', ticker)
            
            # Extract Prices (handle both simple and rich formats)
            qty = Decimal(str(item.get('quantity', 0)))
            curr_price = Decimal(str(item.get('current_price', item.get('price', 0))))
            purch_price = Decimal(str(item.get('purchase_price', 0)))
            curr_val = qty * curr_price
            
            h = Holding(
                broker="bgsaxo",
                ticker=ticker[:20] if ticker else "UNKNOWN",
                name=name[:100] if name else "UNKNOWN",
                asset_type=item.get('asset_type', 'STOCK').upper(),
                quantity=qty,
                currency=item.get('currency', 'EUR'),
                isin=item.get('isin'),
                current_price=curr_price,
                current_value=curr_val,
                purchase_price=purch_price
            )
            db.add(h)
            count += 1
        db.commit()
        logger.info(f"   ✅ Loaded {count} holdings.")
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("\n🚀 STARTING FULL AUTOMATION TEST (BG SAXO)\n")
    
    # 1. Reset
    reset_db_broker("bgsaxo")
    
    # 2. Load Holdings
    load_holdings_hq()
    
    # 3. Load Transactions
    logger.info("\n📜 LOADING TRANSACTIONS (via Subprocess)...")
    import subprocess
    try:
        # Run the standalone loader as a separate process to avoid import/env issues
        subprocess.run([sys.executable, "scripts/load_universal_transactions_standalone.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Transaction Load Failed: {e}")
        return # Stop if load fails
    
    # 4. Reconcile
    logger.info("\n⚖️ RECONCILING...")
    # Also run reconcile via subprocess to ensure clean state
    subprocess.run([sys.executable, "scripts/reconcile_history.py"], check=True)
    
    print("\n🎉 AUTOMATION TEST COMPLETE.")

if __name__ == "__main__":
    main()
