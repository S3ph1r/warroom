import sys
import os
import logging
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Holding, Transaction
from scripts.parse_bgsaxo_csv import parse_bgsaxo_holdings

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("BGSaxoPipeline")

# CONFIG
BGSAXO_DIR = Path(r"d:\Download\BGSAXO")
SCRIPTS_DIR = project_root / "scripts"

def get_latest_files():
    # Find latest CSV (Posizioni*)
    csv_files = list(BGSAXO_DIR.glob("Posizioni*.csv"))
    latest_csv = max(csv_files, key=os.path.getmtime) if csv_files else None
    
    # Find latest PDF (Transactions*)
    pdf_files = list(BGSAXO_DIR.glob("Transactions*.pdf"))
    latest_pdf = max(pdf_files, key=os.path.getmtime) if pdf_files else None
    
    return latest_csv, latest_pdf

def ensure_rules(target_file, script_name):
    """Checks if .rules.json exists, otherwise runs analysis script."""
    rule_file = target_file.with_name(target_file.name + ".rules.json")
    if rule_file.exists():
        logger.info(f"   ✅ Rules found for {target_file.name}")
        return rule_file
    
    logger.info(f"   ⚠️ Rules MISSING for {target_file.name}. Generating via LLM...")
    script_path = SCRIPTS_DIR / script_name
    try:
        subprocess.run([sys.executable, str(script_path), str(target_file)], check=True)
        if rule_file.exists():
            logger.info("   ✅ Rules generated successfully.")
            return rule_file
        else:
            logger.error("   ❌ Failed to generate rules.")
            return None
    except Exception as e:
        logger.error(f"   ❌ Analysis script failed: {e}")
        return None

def clean_db_for_broker(session, broker="BG_SAXO"):
    logger.info(f"🧹 Clearing DB records for {broker}...")
    h_count = session.query(Holding).filter(Holding.broker == broker).delete()
    t_count = session.query(Transaction).filter(Transaction.broker == broker).delete()
    session.commit()
    logger.info(f"   Deleted {h_count} holdings and {t_count} transactions.")

def ingest(csv_file, pdf_file):
    session = SessionLocal()
    clean_db_for_broker(session)
    
    # 1. INGEST HOLDINGS (CSV)
    if csv_file:
        logger.info(f"\n📥 INGESTING CSV: {csv_file.name}")
        try:
            holdings_data = parse_bgsaxo_holdings(csv_file)
            count = 0
            for row in holdings_data:
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
                    source_document=str(csv_file)
                )
                session.add(h)
                count += 1
            session.commit()
            logger.info(f"   ✅ Imported {count} holdings.")
        except Exception as e:
            logger.error(f"   ❌ CSV Ingestion failed: {e}")
            session.rollback()

    # 2. INGEST TRANSACTIONS (PDF)
    if pdf_file:
        logger.info(f"\n📥 INGESTING PDF: {pdf_file.name}")
        parser_script = SCRIPTS_DIR / "parse_bgsaxo_dynamic.py"
        try:
            # Run parser (it saves to .extracted.json)
            subprocess.run([sys.executable, str(parser_script), str(pdf_file)], check=True)
            
            # Load Result
            extracted_json = pdf_file.with_suffix('.extracted.json')
            if not extracted_json.exists():
                raise FileNotFoundError("Extracted JSON not found.")
                
            with open(extracted_json, 'r', encoding='utf-8') as f:
                tx_data = json.load(f)
                
            count = 0
            for row in tx_data:
                # Basic Mapping Logic
                t_type = str(row.get('type') or '').upper()
                qty = Decimal(0)
                price = Decimal(0)
                op = "UNKNOWN"
                
                # Check for Qty/Price in extracted or full text
                # (Reusing logic from test script for robust parsing)
                import re
                # Use a broad regex for the numeric extraction
                details_re = re.compile(r'(Acquista|Vendi|Buy|Sell)(?:-)?(\d+(?:[.,]\d+)?)@(\d+(?:[.,]\d+)?)', re.IGNORECASE)
                search_text = (row.get('product') or '') + " " + (row.get('full_text') or '')
                search_text = search_text.replace(' ', '')
                
                m = details_re.search(search_text)
                if m:
                    action, q_str, p_str = m.groups()
                    qty = Decimal(q_str.replace('.','').replace(',','.'))
                    price = Decimal(p_str.replace('.','').replace(',','.'))
                    op = "BUY" if "ACQUISTA" in action.upper() else "SELL"
                else:
                    # Fallback for Dividends/Deposits
                    if "DIVIDENDO" in t_type: op = "DIVIDEND"
                    elif "DEPOSITO" in t_type: op = "DEPOSIT"
                    elif "COMMISSIONE" in t_type or "COMMISS" in row.get('full_text', '').upper(): op = "FEE"
                    
                    price = Decimal(str(row.get('amount', 0)).replace(',','.')) # Use extracted amount

                t = Transaction(
                    id=uuid.uuid4(),
                    broker="BG_SAXO",
                    ticker=str(row.get('product', 'UNKNOWN'))[:20],
                    isin=row.get('isin')[:12] if row.get('isin') else None,
                    operation=op,
                    quantity=qty,
                    price=price,
                    total_amount=qty*price if op in ['BUY', 'SELL'] else price, # For dividends found amount is total
                    timestamp=datetime.strptime(row.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d'),
                    status="COMPLETED",
                    source_document=str(pdf_file)[:255]
                )
                session.add(t)
                count += 1
            session.commit()
            logger.info(f"   ✅ Imported {count} transactions.")
            
        except Exception as e:
            logger.error(f"   ❌ PDF Ingestion failed: {e}")
            session.rollback()

    session.close()

def main():
    logger.info("==========================================")
    logger.info("   BG SAXO INGESTION PIPELINE (AUTO)      ")
    logger.info("==========================================")
    
    csv_file, pdf_file = get_latest_files()
    
    if not csv_file and not pdf_file:
        logger.error("❌ No CSV or PDF files found in Download folder.")
        sys.exit(1)
        
    logger.info(f"CSV Found: {csv_file.name if csv_file else 'NONE'}")
    logger.info(f"PDF Found: {pdf_file.name if pdf_file else 'NONE'}")
    
    # 1. Ensure Rules Exist
    if csv_file:
        ensure_rules(csv_file, "analyze_csv_structure.py")
    if pdf_file:
        ensure_rules(pdf_file, "analyze_pdf_structure.py")
        
    # 2. Ingest
    ingest(csv_file, pdf_file)
    
    logger.info("\n✅ PIPELINE COMPLETED.")

if __name__ == "__main__":
    main()
