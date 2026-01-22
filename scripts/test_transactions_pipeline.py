"""
TEST ROUTER (TRANSACTIONS ONLY)
1. Runs the Universal Router (should process ONLY the PDF in inbox/bgsaxo).
2. Uses the Deterministic Strategy (updated in Router).
3. Loads the resulting JSON into DB.
"""
import sys
import subprocess
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("TxTest")

# Setup Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

def get_db_url():
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / '.env')
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "warroom")
    return f"postgresql://{user}:{password}@{server}:{port}/{db}"

def reset_tx_only(broker="bgsaxo"):
    logger.info(f"🧨 RESETTING Transactions for broker: {broker}...")
    engine = create_engine(get_db_url())
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM transactions WHERE broker = '{broker}'"))
    logger.info("   ✅ Cleaned.")

def main():
    print("\n🎬 STARTING TRANSACTION-ONLY ROUTER TEST\n")
    
    # 1. Reset
    reset_tx_only("bgsaxo")
    
    # 2. Run Router
    logger.info("📡 RUNNING ROUTER...")
    try:
        # Router will look in inbox/bgsaxo
        # We expect only the PDF there.
        subprocess.run([sys.executable, "scripts/universal_ingestion_router.py"], check=True)
    except subprocess.CalledProcessError:
        logger.error("❌ Router Failed.")
        return

    # 3. Check for Output
    extracted_dir = ROOT_DIR / "data" / "extracted"
    # Find the generated JSON
    files = list(extracted_dir.glob("Transactions*.json"))
    if not files:
        logger.error("❌ No Transaction JSON found!")
        return
    
    # Pick the most recent one if multiple match
    json_path = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    logger.info(f"✅ Found new extracted JSON: {json_path.name}")
    
    # 4. Convert to CSV for Loader (Adapter Step)
    # The standalone loader expects a specific CSV filename.
    import pandas as pd
    import json
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    items = data if isinstance(data, list) else data.get('data', [])
    if not items:
         logger.error("❌ JSON contains no items.")
         return
         
    df = pd.DataFrame(items)
    csv_path = extracted_dir / "BG_SAXO_Transactions_FinalVersion.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"   -> Converted to CSV: {csv_path.name}")

    # 5. Load Transactions
    logger.info("📜 LOADING TO DB...")
    subprocess.run([sys.executable, "scripts/load_universal_transactions_standalone.py"], check=True)
    
    # 6. Reconcile (Optional / Informational since holdings are missing)
    # logger.info("⚖️ RECONCILING (Expect mismatches due to missing holdings)...")
    # subprocess.run([sys.executable, "scripts/reconcile_history.py"], check=False)

    print("\n🎉 TRANSACTION PIPELINE TEST COMPLETE.")

if __name__ == "__main__":
    main()
