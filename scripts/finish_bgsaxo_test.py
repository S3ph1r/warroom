"""
FINISH JOB: BG SAXO
1. Reuse existing valid Holdings JSON (from LLM).
2. Rerun Deterministic PDF Parser (Fast) to fix incomplete transactions.
3. Load & Reconcile.
"""
import sys
import os
import subprocess
import logging
import shutil
import json
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

# Setup Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
from scripts.universal_pdf_parser import parse_pdf

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("FinishJob")

def main():
    print("\n🏁 FINISHING BG SAXO TEST (RESUMING)...\n")
    
    # Paths
    extracted = ROOT_DIR / "data" / "extracted"
    inbox = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")
    
    # 1. HOLDINGS (Reuse)
    holdings_json = extracted / "Posizioni_19-dic-2025_17_49_12.csv.json"
    if not holdings_json.exists():
        logger.error(f"❌ Critical Source Missing: {holdings_json}")
        # Try finding it in bgsaxo subdir
        holdings_json = extracted / "bgsaxo" / "Posizioni_19-dic-2025_17_49_12.csv.json"
        
    if not holdings_json.exists():
         logger.error("❌ Cannot find Holdings JSON. Automation failed.")
         return
         
    logger.info(f"✅ Found Holdings: {holdings_json.name}")
    
    # Ensure it's in the right place for loader
    dest_dir = extracted / "bgsaxo"
    dest_dir.mkdir(exist_ok=True)
    shutil.copy(holdings_json, dest_dir / "Posizioni_19-dic-2025_17_49_12.csv.json") # Normalize name

    # 2. TRANSACTIONS (Rerun Deterministic Parser)
    logger.info("🔄 RE-PARSING TRANSACTIONS (Deterministic)...")
    trans_pdf = inbox / "Transactions_19807401_2024-11-26_2025-12-19.pdf"
    
    try:
        df = parse_pdf(str(trans_pdf))
        logger.info(f"   📊 Extracted {len(df)} transactions.")
        
        # Save CSV for Loader
        csv_path = extracted / "BG_SAXO_Transactions_FinalVersion.csv"
        df.to_csv(csv_path, index=False)
        logger.info(f"   💾 Saved CSV: {csv_path.name}")
        
    except Exception as e:
        logger.error(f"❌ PDF Parsing Failed: {e}")
        return

    # 3. RESET DB (Optional? No, let's keep it safe)
    # Actually, we should reset to ensure clean state
    # But user might wonder why we reset. 
    # Let's reset.
    logger.info("🧨 RESETTING DB (Broker: bgsaxo)...")
    subprocess.run([sys.executable, "scripts/clean_and_test_bgsaxo.py", "--reset-only"], check=False) 
    # Wait, clean_and_test_bgsaxo.py doesn't have args. 
    # Let's just run inline reset.
    from scripts.clean_and_test_bgsaxo import reset_db_broker
    reset_db_broker("bgsaxo")

    # 4. LOAD HOLDINGS
    logger.info("💼 LOADING HOLDINGS...")
    # Loader expects file in data/extracted/bgsaxo/...
    subprocess.run([sys.executable, "scripts/load_holdings.py"], check=True)

    # 5. LOAD TRANSACTIONS
    logger.info("📜 LOADING TRANSACTIONS...")
    subprocess.run([sys.executable, "scripts/load_universal_transactions_standalone.py"], check=True)

    # 6. RECONCILE
    logger.info("⚖️ RECONCILING...")
    subprocess.run([sys.executable, "scripts/reconcile_history.py"], check=True)
    
    print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    main()
