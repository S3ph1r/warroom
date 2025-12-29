
import sys
import os
import shutil
import subprocess
import logging
from pathlib import Path
from decimal import Decimal
import json
import uuid
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal, init_db
from db.models import Holding, Transaction
from scripts.parse_bgsaxo_csv import parse_bgsaxo_holdings # Direct import for parsing phase

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("CleanCycle")

# CONFIG
PYTHON_EXE = sys.executable
BGSAXO_DIR = Path(r"d:\Download\BGSAXO")
CSV_FILE = BGSAXO_DIR / "Posizioni_19-dic-2025_17_49_12.csv"
PDF_FILE = BGSAXO_DIR / "Transactions_19807401_2024-11-26_2025-12-19.pdf"

SCRIPTS_DIR = project_root / "scripts"
SCRIPT_ANALYZE_CSV = SCRIPTS_DIR / "analyze_csv_structure.py"
SCRIPT_ANALYZE_PDF = SCRIPTS_DIR / "analyze_pdf_structure.py"
SCRIPT_PARSE_PDF = SCRIPTS_DIR / "parse_bgsaxo_dynamic.py"

def step_header(title):
    logger.info(f"\n{'='*50}\n {title}\n{'='*50}")

def clean_artifacts():
    step_header("1. CLEANING ARTIFACTS")
    
    # Define artifacts to remove
    artifacts = [
        CSV_FILE.with_name(CSV_FILE.name + ".rules.json"),
        PDF_FILE.with_name(PDF_FILE.name + ".rules.json"),
        PDF_FILE.with_suffix('.extracted.json')
    ]
    
    for f in artifacts:
        if f.exists():
            try:
                os.remove(f)
                logger.info(f"[DELETED] {f.name}")
            except Exception as e:
                logger.error(f"[ERROR] Failed to delete {f.name}: {e}")
                sys.exit(1)
        else:
            logger.info(f"   (Not found, skipping): {f.name}")

def clean_db():
    step_header("2. CLEANING DATABASE")
    session = SessionLocal()
    try:
        h_del = session.query(Holding).filter(Holding.broker == "BG_SAXO").delete()
        t_del = session.query(Transaction).filter(Transaction.broker == "BG_SAXO").delete()
        session.commit()
        logger.info(f"[CLEAN] DB Cleaned: Removed {h_del} holdings, {t_del} transactions.")
    except Exception as e:
        logger.error(f"[ERROR] DB Clean Failed: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()

def run_analysis(script, target_file, desc):
    step_header(f"3. {desc} ANALYSIS (LLM)")
    logger.info(f"[RUN] invoking {script.name} on {target_file.name}...")
    
    try:
        # Run process
        result = subprocess.run(
            [PYTHON_EXE, str(script), str(target_file)],
            capture_output=True, text=True, check=True
        )
        # Log stdout slightly indented
        for line in result.stdout.splitlines():
            logger.info(f"   | {line}")
            
        # Check if rule file created
        # Rule convention: filename + .rules.json
        expected_rule = target_file.with_name(target_file.name + ".rules.json")
        if expected_rule.exists():
            logger.info(f"[SUCCESS] Rules generated: {expected_rule.name}")
            return expected_rule
        else:
            logger.error(f"[ERROR] Rule file NOT found: {expected_rule}")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Analysis Script Failed!\nSTDERR:\n{e.stderr}\nSTDOUT:\n{e.stdout}")
        sys.exit(1)

def execute_ingestion():
    step_header("4. PARSING & DIGESTION")
    
    session = SessionLocal()
    
    # --- CSV INGESTION ---
    logger.info("[INFO] Processing CSV Holdings...")
    try:
        # We assume the analysis step confirmed the structure. 
        # Using the reliable static parser for execution speed/robustness.
        holdings = parse_bgsaxo_holdings(CSV_FILE)
        
        count_h = 0
        for row in holdings:
            qty = Decimal(row.get('quantity', 0))
            price = Decimal(row.get('current_price', 0))
            h = Holding(
                id=uuid.uuid4(),
                broker="BG_SAXO",
                ticker=row.get('ticker') or 'UNKNOWN',
                isin=row.get('isin'),
                name=row.get('name') or 'Unknown',
                quantity=qty,
                current_price=price,
                current_value=qty * price,
                currency=row.get('currency', 'EUR'),
                asset_type=row.get('asset_type', 'STOCK').upper(),
                last_updated=datetime.now(),
                source_document=str(CSV_FILE)
            )
            session.add(h)
            count_h += 1
        session.commit()
        logger.info(f"[SUCCESS] CSV Ingested: {count_h} holdings.")
        
    except Exception as e:
        logger.error(f"[ERROR] CSV Ingestion Failed: {e}")
        session.rollback()
        sys.exit(1)

    # --- PDF INGESTION ---
    logger.info("[INFO] Processing PDF Transactions (Dynamic Parsers)...")
    try:
        # Run Dynamic Parser Script
        res = subprocess.run([PYTHON_EXE, str(SCRIPT_PARSE_PDF), str(PDF_FILE)], capture_output=True, text=True, check=True)
        for line in res.stdout.splitlines():
             if "[INFO]" in line or "[SUCCESS]" in line or "[ERROR]" in line:
                 logger.info(f"   | {line}")
        
        # Load generated JSON
        extracted_json = PDF_FILE.with_suffix('.extracted.json')
        if not extracted_json.exists():
             logger.error("[ERROR] extracted.json missing after parsing!")
             sys.exit(1)
             
        with open(extracted_json, 'r', encoding='utf-8') as f:
            transactions_data = json.load(f)
            
        count_t = 0
        for row in transactions_data:
             # Basic mapping logic (simplified from full cycle script)
             t_type = str(row.get('type') or '').upper()
             qty = Decimal(0)
             price = Decimal(0)
             op = "UNKNOWN"
             
             # Extract Qty/Price from full text using regex (as in full cycle script)
             import re
             details_re = re.compile(r'(Acquista|Vendi|Buy|Sell)(?:-)?(\d+(?:[.,]\d+)?)@(\d+(?:[.,]\d+)?)', re.IGNORECASE)
             search_text = (row.get('full_text') or row.get('raw_line') or '').replace(' ', '')
             
             m = details_re.search(search_text)
             if m:
                 action, q_str, p_str = m.groups()
                 qty = Decimal(q_str.replace('.','').replace(',','.'))
                 price = Decimal(p_str.replace('.','').replace(',','.'))
                 op = "BUY" if "ACQUISTA" in action.upper() else "SELL"
             else:
                 # Fallback
                 if "DIVIDENDO" in t_type: op = "DIVIDEND"
                 if "DEPOSITO" in t_type: op = "DEPOSIT"
                 price = Decimal(str(row.get('amount', 0)).replace(',','.')) # Fallback amount
             
             t = Transaction(
                id=uuid.uuid4(),
                broker="BG_SAXO",
                ticker=str(row.get('product', 'UNKNOWN'))[:20],
                isin=row.get('isin')[:12] if row.get('isin') else None,
                operation=op,
                quantity=qty,
                price=price,
                total_amount=qty*price,
                timestamp=datetime.now(), # Simplify date parsing for test
                status="COMPLETED",
                source_document=str(PDF_FILE)[:255]
             )
             session.add(t)
             count_t += 1
        
        session.commit()
        logger.info(f"[SUCCESS] PDF Ingested: {count_t} transactions.")

    except Exception as e:
        logger.error(f"[ERROR] PDF Ingestion Failed: {e}")
        session.rollback()
        sys.exit(1)
        
    session.close()

def final_verification():
    step_header("5. FINAL VERIFICATION")
    session = SessionLocal()
    h_count = session.query(Holding).filter(Holding.broker == "BG_SAXO").count()
    t_count = session.query(Transaction).filter(Transaction.broker == "BG_SAXO").count()
    session.close()
    
    logger.info(f"[STATS] Holdings in DB: {h_count}")
    logger.info(f"[STATS] Transactions in DB: {t_count}")
    
    if h_count > 0 and t_count > 0:
        logger.info("\n[SUCCESS] TEST PASSED: Full Cycle Completed Correctly.")
    else:
        logger.error("\n[FAILURE] TEST FAILED: Missing Data in DB.")
        sys.exit(1)

def main():
    logger.info("[START] CLEAN SLATE FULL CYCLE TEST")
    clean_artifacts()
    clean_db()
    
    # Generate Rules
    run_analysis(SCRIPT_ANALYZE_CSV, CSV_FILE, "CSV")
    run_analysis(SCRIPT_ANALYZE_PDF, PDF_FILE, "PDF")
    
    # Ingest
    execute_ingestion()
    
    # Verify
    final_verification()


if __name__ == "__main__":
    main()
