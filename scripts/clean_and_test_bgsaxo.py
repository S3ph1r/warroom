"""
CLEAN SLATE TEST: BG SAXO
1. Clean Extracted Data (Done via cmd)
2. Reset DB
3. Run Router (LLM for CSV, Det. for PDF)
4. Load & Reconcile
"""
import sys
import os
import subprocess
import logging
import shutil
from pathlib import Path
from sqlalchemy import create_engine, text

# Setup Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("CleanSlateTest")

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

def main():
    print("\n🧼 STARTING CLEAN SLATE TEST (BG SAXO)\n")
    
    # 1. Reset DB
    reset_db_broker("bgsaxo")
    
    # 2. Run Router
    logger.info("📡 RUNNING ROUTER (This may take time for CSV LLM extraction)...")
    try:
        subprocess.run([sys.executable, "scripts/universal_ingestion_router.py"], check=True)
        # logger.info("   ⏭️ SKIPPING ROUTER (Using existing extracted files)...")
    except subprocess.CalledProcessError:
        logger.error("❌ Router failed.")
        return

    # 3. Verify & Move Outputs
    # The Router saves to data/extracted/
    # We expect:
    # - Posizioni_19-dic-2025_17_49_12.csv.json (Holdings)
    # - Transactions_...pdf.json (Transactions)
    
    extracted = ROOT_DIR / "data" / "extracted"
    holdings_src = extracted / "Posizioni_19-dic-2025_17_49_12.csv.json"
    
    # Find the transaction file (name might vary slightly)
    trans_files = list(extracted.glob("Transactions*.json"))
    trans_src = trans_files[0] if trans_files else None

    if not holdings_src.exists():
        logger.warning("⚠️ Holdings JSON not generated! Skipping Holdings Load...")
        has_holdings = False
    else:
        has_holdings = True
        
    if not trans_src:
        logger.error("❌ Transactions JSON not generated!")
        return

    # Move to bgsaxo subfolder for loaders to find them (mimicking manual organization if needed)
    # Actually, loaders scan extracted/ or specific paths.
    # Let's ensure 'load_holdings.py' finds the right file. 
    # It prefers 'data/extracted/bgsaxo/Posizioni...'.
    dest_dir = extracted / "bgsaxo"
    dest_dir.mkdir(exist_ok=True)
    
    # Check if Holdings already exists in bgsaxo subfolder (avoid re-copying)
    holdings_in_dest = dest_dir / "Posizioni_19-dic-2025_17_49_12.csv.json"
    if holdings_in_dest.exists():
        logger.info(f"   ✅ Holdings JSON already in {dest_dir}")
        has_holdings = True
    elif has_holdings:
        shutil.copy(holdings_src, holdings_in_dest)
        logger.info(f"   Copied Holdings to {dest_dir}")

    # Transactions: standalone loader expects 'BG_SAXO_Transactions_FinalVersion.csv' in extracted/
    # But Router output is JSON.
    # We need to convert JSON -> CSV for the loader (or update loader).
    # Since we verified PDF parser works, let's just convert it here quickly.
    
    import pandas as pd
    import json
    
    logger.info("   Converting Transaction JSON to CSV for Loader...")
    with open(trans_src, 'r', encoding='utf-8') as f:
        t_data = json.load(f)
        
    # Router output is { ..., data: [...] } OR list [...]
    if isinstance(t_data, dict):
        t_items = t_data.get('data', [])
    else:
        t_items = t_data
        
    if t_items:
        logger.info(f"   🔍 JSON First Item Keys: {list(t_items[0].keys())}")
        logger.info(f"   🔍 JSON First Item Sample: {t_items[0]}")
        
    df = pd.DataFrame(t_items)
    csv_path = extracted / "BG_SAXO_Transactions_FinalVersion.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"   ✅ Saved CSV to {csv_path}")

    # 4. Load Holdings
    if has_holdings:
        logger.info("💼 LOADING HOLDINGS...")
        subprocess.run([sys.executable, "scripts/load_holdings.py"], check=True)
    else:
        logger.info("⏭️ SKIP LOADING HOLDINGS (File missing)")

    # 5. Load Transactions
    logger.info("📜 LOADING TRANSACTIONS...")
    subprocess.run([sys.executable, "scripts/load_universal_transactions_standalone.py"], check=True)

    # 6. Reconcile
    logger.info("⚖️ RECONCILING...")
    subprocess.run([sys.executable, "scripts/reconcile_history.py"], check=True)
    
    print("\n🎉 CLEAN SLATE TEST COMPLETE.")

if __name__ == "__main__":
    main()
