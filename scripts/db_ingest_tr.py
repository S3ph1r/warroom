import sys
import json
import uuid
import logging
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal, init_db
from db.models import Holding, Transaction
from utils.parsing import robust_parse_decimal
from services.price_service_v5 import resolve_asset_info

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("DB_Ingest_TR")

BROKER_NAME = "TRADE_REPUBLIC"

def parse_decimal(val):
    """Use centralized robust numeric parser."""
    return robust_parse_decimal(val)

def map_operation(tx_type, description):
    desc = description.lower()
    t = tx_type.lower()
    
    if "buy" in desc or "acquisto" in desc:
        return "BUY"
    if "sell" in desc or "vendita" in desc:
        return "SELL"
    if "dividendi" in t or "cedola" in t or "rendimento" in t or "dividend" in desc:
        return "DIVIDEND"
    if "interessi" in t or "interest" in desc:
        return "INTEREST"
    
    # Bonifico / Transfers
    if "bonifico" in t or "transfer" in desc or "deposito" in desc:
        if "outgoing" in desc or "uscita" in desc or "prelievo" in desc:
            return "WITHDRAW"
        return "DEPOSIT"
        
    if "imposta" in t or "tasse" in t or "tax" in desc:
        return "FEE"
    
    return "OTHER"

def ingest_data(pdf_path):
    logger.info(f"🚀 Starting DB Ingestion for {pdf_path.name}")
    init_db()
    session = SessionLocal()
    
    holdings_file = pdf_path.with_suffix('.holdings.json')
    tx_file = pdf_path.with_suffix('.extracted.json')
    
    counts = {"holdings": 0, "transactions": 0}
    
    try:
        # 1. HOLDINGS
        if holdings_file.exists():
            logger.info(f"📥 Loading Holdings from {holdings_file.name}...")
            # Simple delete for THIS BROKER to ensure clean snapshot
            session.query(Holding).filter(Holding.broker == BROKER_NAME).delete()
            
            with open(holdings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    isin = item.get('isin')
                    # Resolve real ticker and name from ISIN
                    info = resolve_asset_info(isin, isin)
                    
                    h = Holding(
                        broker=BROKER_NAME,
                        ticker=info['ticker'],
                        isin=isin,
                        name=info['name'],
                        quantity=parse_decimal(item.get('quantity')),
                        current_price=parse_decimal(item.get('current_price')),
                        current_value=parse_decimal(item.get('current_val')),
                        asset_type="STOCK",
                        source_document=pdf_path.name
                    )
                    session.add(h)
                    counts["holdings"] += 1
        
        # 2. TRANSACTIONS
        if tx_file.exists():
            logger.info(f"📥 Loading Transactions from {tx_file.name}...")
            with open(tx_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    description = item.get('description', '')
                    full_text = item.get('full_text', '')
                    raw_date = item.get('date', '').lower()
                    
                    # --- DATE PARSING ---
                    ts = None
                    try:
                        # Attempt standard YYYY-MM-DD
                        ts = datetime.strptime(raw_date, "%Y-%m-%d")
                    except:
                        # Month mapping (Italian/English mix)
                        months = {
                            "gen":1, "feb":2, "mar":3, "apr":4, "mag":5, "giu":6, 
                            "lug":7, "ago":8, "set":9, "ott":10, "nov":11, "dic":12,
                            "jan":1, "mar":3, "may":5, "jun":6, "jul":7, "aug":8, "sep":9, "oct":10, "dec":12
                        }
                        parts = raw_date.split()
                        if len(parts) >= 2:
                            try:
                                day = int(parts[0])
                                # Validation: day must be 1..31
                                if not (1 <= day <= 31):
                                    raise ValueError(f"Invalid day: {day}")
                                    
                                month_str = parts[1]
                                month = None
                                for k, v in months.items():
                                    if month_str.startswith(k):
                                        month = v
                                        break
                                
                                if not month:
                                    raise ValueError(f"Invalid month: {month_str}")
                                
                                # Year detection
                                year = 2024
                                if "2023" in full_text: year = 2023
                                if "2025" in full_text: year = 2025
                                
                                ts = datetime(year, month, day)
                            except Exception as e:
                                logger.warning(f"      ⚠️ Skipping transaction due to bad date: '{raw_date}' ({e})")
                                continue
                    
                    if not ts:
                        continue

                    # --- OPERATION & AMOUNT ---
                    val = parse_decimal(item.get('amount'))
                    op = map_operation(item.get('type', ''), description)
                    
                    if op == "DEPOSIT" and val < 0:
                        op = "WITHDRAW"
                        val = abs(val)

                    # --- ISIN & QUANTITY EXTRACTION (from description if possible) ---
                    isin_match = re.search(r'[A-Z]{2}[A-Z0-9]{9}\d', description)
                    isin = isin_match.group(0) if isin_match else None
                    
                    qty = Decimal(0)
                    qty_match = re.search(r'quantity:\s*([\d,.]+)', description, re.IGNORECASE)
                    if qty_match:
                        # TR quantity is usually the FIRST number after "quantity:"
                        # Use robust parser but handle the extra word removal if needed
                        q_str = qty_match.group(1).split()[0] # Take only the first word
                        qty = robust_parse_decimal(q_str)

                    t = Transaction(
                        broker=BROKER_NAME,
                        ticker=isin or "CASH",
                        isin=isin,
                        operation=op,
                        quantity=qty,
                        price=val / qty if (qty and val and qty != 0) else Decimal(0),
                        total_amount=val,
                        timestamp=ts,
                        source_document=pdf_path.name,
                        notes=description[:255]
                    )
                    session.add(t)
                    counts["transactions"] += 1
                    
        session.commit()
        logger.info(f"✅ Ingestion complete: {counts['holdings']} holdings, {counts['transactions']} txns.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Ingestion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db_ingest_tr.py <pdf_file>")
        sys.exit(1)
    
    ingest_data(Path(sys.argv[1]))
