import os
import sys
import json
import logging
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal, init_db
from db.models import Holding, Transaction

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("TR_Orchestrator")

def cleanup_db(broker_name):
    logger.info(f"🧹 Cleaning up DB records for broker: {broker_name}...")
    init_db()
    session = SessionLocal()
    try:
        holdings_deleted = session.query(Holding).filter(Holding.broker == broker_name).delete()
        txns_deleted = session.query(Transaction).filter(Transaction.broker == broker_name).delete()
        session.commit()
        logger.info(f"   ✅ Deleted {holdings_deleted} holdings and {txns_deleted} transactions.")
    except Exception as e:
        session.rollback()
        logger.error(f"   ❌ DB Cleanup failed: {e}")
    finally:
        session.close()

def invalidate_snapshot():
    snapshot_path = project_root / "data" / "portfolio_snapshot.json"
    if snapshot_path.exists():
        try:
            snapshot_path.unlink()
            logger.info("♻️  Portfolio snapshot invalidated (deleted). Backend will rebuild on next request.")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate snapshot: {e}")

def run_command(cmd_list):
    try:
        subprocess.run(cmd_list, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Command failed: {' '.join(cmd_list)}")
        return False

def orchestrate(pdf_path_str):
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        return

    # CLEANUP OLD RESULTS
    for suffix in ['.holdings.json', '.extracted.json', '.classification.json', '.rules.json', '.vision.rules.json']:
        old_file = pdf_path.with_suffix(suffix)
        if old_file.exists():
            old_file.unlink()
            logger.info(f"🧹 Removed old file: {old_file.name}")

    # CLEANUP DB
    cleanup_db("TRADE_REPUBLIC")

    # PHASE 1: ROUTER
    logger.info("🚦 Starting Phase 1: Router...")
    if not run_command([sys.executable, "scripts/analyze_tr_structure.py", str(pdf_path)]):
        return

    # READ CLASSIFICATION
    class_file = pdf_path.with_suffix('.classification.json')
    if not class_file.exists():
        logger.error("Router failed to produce classification file.")
        return
    
    with open(class_file, 'r', encoding='utf-8') as f:
        classification = json.load(f)

    has_transactions = classification.get("has_transactions", False)
    has_holdings = classification.get("has_holdings", False)

    # EXECUTION PATHS
    
    # 1. TRANSACTIONS PATH
    if has_transactions:
        logger.info("📈 Processing Transactions path...")
        
        # Phase 3: Vision Rules
        logger.info("👁️ Running Vision-based Rule Generation...")
        run_command([sys.executable, "scripts/analyze_tr_vision.py", str(pdf_path)])
        
        # Phase 4: Deterministic Parser
        logger.info("🚜 Running extraction engine...")
        run_command([sys.executable, "scripts/parse_tr_dynamic.py", str(pdf_path)])

    # 2. HOLDINGS PATH
    if has_holdings:
        logger.info("📸 Processing Holdings path...")
        run_command([sys.executable, "scripts/extract_tr_holdings.py", str(pdf_path)])
    else:
        logger.warning("ℹ️ No holdings section detected in document.")

    # 3. DB INGESTION
    logger.info("📥 Starting Database Ingestion...")
    run_command([sys.executable, "scripts/db_ingest_tr.py", str(pdf_path)])

    # 4. RECONSTRUCTION (If transactions only)
    if has_transactions and not has_holdings:
        print("\n" + "!"*60)
        print(" ⚠️  ATTENZIONE: Manca la foto del portafoglio (Holdings).")
        print(" Posso ricostruire la situazione attuale aggregando i movimenti storici.")
        print("!"*60)
        ans = input(" Vuoi procedere con la ricostruzione? (S/N): ").strip().upper()
        if ans == 'S':
            run_command([sys.executable, "scripts/reconstruct_holdings_from_tx.py", "TRADE_REPUBLIC"])

    # 5. INVALIDATE SNAPSHOT
    invalidate_snapshot()

    logger.info("✅ Trade Republic Ingestion Cycle Completed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_tr_full.py <pdf_file>")
        sys.exit(1)
    orchestrate(sys.argv[1])
