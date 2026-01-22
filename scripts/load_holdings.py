import sys
import json
import logging
from pathlib import Path
from decimal import Decimal

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.database import SessionLocal
from db.models import Transaction, Holding

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_holdings_from_csv_json(broker_name):
    logger.info(f"💼 LOADING HOLDINGS: {broker_name.upper()}")
    
    # Locate the extracted JSON
    extracted_dir = ROOT_DIR / "data" / "extracted"
    
    # Priority 1: Python-parsed file (most accurate)
    python_parsed = extracted_dir / f"{broker_name.upper()}_Holdings_Python.json"
    if python_parsed.exists():
        valid_file = python_parsed
        logger.info(f"   ✅ Using Python-parsed file")
    else:
        # Priority 2: Check broker subfolder
        broker_dir = extracted_dir / broker_name
        if broker_dir.exists():
            files = list(broker_dir.glob("*Posizioni*.json")) + list(broker_dir.glob("*Holdings*.json"))
        else:
            # Priority 3: Check root extracted folder
            files = list(extracted_dir.glob(f"*{broker_name}*Holdings*.json")) + \
                    list(extracted_dir.glob(f"*{broker_name}*Posizioni*.json"))
        
        valid_file = None
        for f in files:
            if f.name.endswith(".csv.json") or "Holdings" in f.name:
                valid_file = f
                break
        
        if not valid_file and files:
            valid_file = files[0]
        
    if not valid_file or not valid_file.exists():
        logger.error(f"❌ No valid Holdings JSON found for {broker_name}")
        return

    logger.info(f"   Source: {valid_file.name}")

    with open(valid_file, 'r', encoding='utf-8') as f:
        content = json.load(f)
        
    items = content.get('data', []) or content.get('holdings', [])
    if not items:
        # Maybe root list?
        if isinstance(content, list): items = content
        else:
            logger.error(f"❌ JSON has no 'data' or 'holdings' list. Keys found: {list(content.keys())}")
            return

    db = SessionLocal()
    try:
        # 1. PURGE EXISTING HOLDINGS
        logger.info(f"   Purging existing holdings for {broker_name}...")
        db.query(Holding).filter(Holding.broker == broker_name).delete()
        db.commit()
        
        # 2. INSERT CLEAN HOLDINGS
        logger.info(f"   Inserting {len(items)} assets...")
        
        for item in items:
            # Try ticker first, then name as fallback
            ticker = item.get('ticker') or item.get('symbol') or item.get('name', 'UNKNOWN')
            if not ticker or ticker == 'UNKNOWN': 
                continue
            
            # Truncate ticker/name if needed
            if len(ticker) > 20: ticker = ticker[:20]
            
            # Validate ISIN
            isin = item.get('isin')
            if isin:
                isin = str(isin).strip().upper()
                # Some ISINs might be dirty, basic length check
                if len(isin) < 12: 
                    logger.warning(f"   ⚠️ Invalid ISIN length '{isin}' for {ticker}")
                    isin = None
                else:
                    isin = isin[:12] # Take first 12 chars if longer (dirty)
                
            qty = Decimal(str(item.get('quantity', 0)))
            curr_price = Decimal(str(item.get('price', 0)))
            currency = item.get('currency', 'EUR')
            
            # Calculate Value
            curr_val = qty * curr_price
            
            h = Holding(
                broker=broker_name,
                ticker=ticker,
                name=item.get('name', ticker)[:100], # Trucate name just in case
                asset_type=item.get('asset_type', 'STOCK').upper(),
                quantity=qty,
                currency=currency,
                isin=isin,
                current_price=curr_price,
                current_value=curr_val,
                purchase_price=Decimal(0), # Missing in CSV
                purchase_date=None, # Missing in CSV
                last_updated=None,
                source_document=valid_file.name[:255]
            )
            db.add(h)
            
        db.commit()
        logger.info("✅ Holdings Load Complete.")
        
    except Exception as e:
        logger.error(f"❌ Error loading Holdings: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    load_holdings_from_csv_json("bgsaxo")
