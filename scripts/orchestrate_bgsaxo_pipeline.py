"""
Orchestrate BG SAXO Ingestion Pipeline
End-to-End Test: Inbox -> Router -> DB -> Reconciliation
"""
import sys
import os
import subprocess
import logging
from pathlib import Path
from sqlalchemy import create_engine, text

# Setup Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Orchestrator")

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
    print("\n🎬 STARTING ORCHESTRATION: BG SAXO INBOX -> DB\n")
    
    # 1. Reset
    reset_db_broker("bgsaxo")
    
    # 2. Router Execution
    logger.info("📡 ROUTING FILES IN INBOX...")
    try:
        # Calls the router which will process G:\...\inbox\bgsaxo
        subprocess.run([sys.executable, "scripts/universal_ingestion_router.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Router Failed: {e}")
        return

    # 3. Locate Generated JSONs
    # The Router saves to data/extracted/ (filename + .json)
    extracted_dir = ROOT_DIR / "data" / "extracted"
    
    holdings_json = extracted_dir / "Posizioni_19-dic-2025_17_49_12.csv.json"
    transactions_json = extracted_dir / "Transactions_19807401_2024-11-26_2025-12-19.pdf.json"
    
    if not holdings_json.exists():
        logger.error(f"❌ Holdings JSON missing: {holdings_json}")
        return
    if not transactions_json.exists():
        logger.error(f"❌ Transactions JSON missing: {transactions_json}")
        return

    # 4. Load Holdings (Source of Truth)
    logger.info(f"\n💼 LOADING HOLDINGS from {holdings_json.name}...")
    # We use valid loader logic but point it to this file
    # We can reuse the load_holdings script or just insert it here.
    # Let's reuse the robust load_holdings script if possible, forcing the path.
    # To keep it simple and robust, let's call load_holdings script via subprocess but we need to ensure it picks THIS file.
    # The load_holdings script has logic to find "Posizioni*". It should pick it up from extracted/bgsaxo if we move it there.
    # But Router saves to extracted/ directly.
    # Let's just use the load logic inline or specific loader.
    # Actually, let's use the 'load_holdings.py' script and ensure it finds the file.
    # The script looks in data/extracted. It should find it.
    subprocess.run([sys.executable, "scripts/load_holdings.py"], check=True)
    
    # 5. Load Transactions
    logger.info(f"\n📜 LOADING TRANSACTIONS from {transactions_json.name}...")
    # We have 'load_universal_transactions_standalone.py' but it expects CSV.
    # The Router outputs JSON (via parser). 
    # Wait, 'universal_pdf_parser' outputs CSV as side effect? No, it returns JSON.
    # But 'load_universal_transactions_standalone.py' loads from "BG_SAXO_Transactions_FinalVersion.csv".
    # I need a loader that loads from the JSON output of the Router, OR ensure Router produces the CSV.
    # The 'universal_pdf_parser' DOES produce a CSV as side effect usually.
    # Let's check if the Router produced the CSV.
    # If not, we might need to convert JSON to DB.
    # Alternatively, let's use a loader that consumes the JSON.
    # But we don't have a "load_json_transactions.py".
    # Let's assume for this test we use the CSV if available, or write a quick JSON loader.
    # Let's check if universal_pdf_parser saves CSV.
    # It seems to save to CSV in its main block. But via function call?
    # Function `parse_pdf_deterministic` returns list of dicts.
    # The Router saves this list to JSON.
    # So we have JSON transactions.
    # I will add a quick JSON loading function here.
    
    import pandas as pd
    from scripts.load_universal_transactions_standalone import get_db_url_inline
    
    # Load JSON to DF
    with open(transactions_json, 'r', encoding='utf-8') as f:
        t_data = json.load(f)
    
    df = pd.DataFrame(t_data)
    # Ensure mapping logic is present
    # We can reuse logic from standalone script but adapted for DF input
    # Or just write to CSV and call standalone script (easiest integration)
    temp_csv = extracted_dir / "temp_router_transactions.csv"
    df.to_csv(temp_csv, index=False)
    
    # Patch standalone loader to read this temp csv?
    # Or just copy it to "BG_SAXO_Transactions_FinalVersion.csv"
    target_csv = extracted_dir / "BG_SAXO_Transactions_FinalVersion.csv"
    df.to_csv(target_csv, index=False)
    
    # Now call standard loader
    subprocess.run([sys.executable, "scripts/load_universal_transactions_standalone.py"], check=True)

    # 6. Reconcile
    logger.info("\n⚖️ RECONCILING...")
    subprocess.run([sys.executable, "scripts/reconcile_history.py"], check=True)
    
    print("\n🎉 ORCHESTRATION COMPLETE.")

if __name__ == "__main__":
    main()
