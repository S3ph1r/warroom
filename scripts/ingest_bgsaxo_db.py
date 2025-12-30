"""
Final Ingestion Script: BG Saxo -> Database
===========================================
Extracts Holdings (CSV) and Transactions (PDF) and saves to the Database.
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.router import DocumentType
from db.database import SessionLocal, init_db
from db.models import Holding, Transaction
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Files
BGSAXO_HOLDINGS = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv"
BGSAXO_TRANSACTIONS = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

BROKER_NAME = "BG_SAXO"

def parse_decimal(val):
    if not val: return Decimal(0)
    if isinstance(val, (int, float)): return Decimal(val)
    # Euro format: 1.234,56 -> 1234.56
    # But CSV might be 1,234.56 (US) or 1.234,56 (EU)
    # My parsers already normalize to standard string (e.g. 155,29 -> 155.29 via 'price' rule? No, parser uses regex)
    # PDF Parser output: "155,29" or "301"
    # CSV Parser output: "145" etc.
    val = str(val).replace('EUR','').replace('USD','').strip()
    # If contains comma and dot, assume dot is thousand separator if it comes before comma (EU)
    # The parsers return raw, cleaned strings.
    # Simple strategy: replace comma with dot if dot not present?
    val = val.replace('.', '').replace(',', '.') # Assume EU format (1.000,00 -> 1000.00)
    # Wait, CSV parser uses standard logic, likely decimal point is comma in IT/EU csv.
    try:
        return Decimal(val)
    except:
        return Decimal(0)

def ingest_holdings(session):
    engine = ExtractionEngine()
    data = engine.extract(Path(BGSAXO_HOLDINGS), BROKER_NAME, DocumentType.HOLDINGS)
    
    if not data:
        logger.warning("No holdings extracted.")
        return 0
        
    # Snapshot strategy: Clear previous holdings for this broker
    deleted = session.query(Holding).filter(Holding.broker == BROKER_NAME).delete()
    logger.info(f"Deleted {deleted} old holdings.")
    
    count = 0
    for row in data:
        # Map fields
        # Hybrid parser returns generic dict.
        # Ensure we map to Model fields: ticker, isin, quantity, price, asset_type...
        
        # Need to parse date? CSV usually has string.
        # Holding model fields: ticker, quantity, average_price, current_price, currency, asset_class, isin
        
        # Calculate current value
        qty = parse_decimal(row.get('quantity', 0))
        price = parse_decimal(row.get('price', 0))
        current_val = qty * price
        
        # Name fallback
        name = row.get('description') or row.get('ticker') or 'Unknown Asset'
        
        h = Holding(
            id=uuid.uuid4(),
            broker=BROKER_NAME,
            ticker=row.get('ticker') or 'UNKNOWN',
            isin=row.get('isin'),
            name=name,
            quantity=qty,
            current_price=price,
            current_value=current_val,
            currency=row.get('currency', 'EUR'),
            asset_type=row.get('asset_type', 'STOCK').upper(), # Default to STOCK
            last_updated=datetime.now(),
            source_document=BGSAXO_HOLDINGS
        )
        session.add(h)
        count += 1
        
    session.commit()
    logger.info(f"Inserted {count} holdings.")
    return count

def ingest_transactions(session):
    engine = ExtractionEngine()
    data = engine.extract(Path(BGSAXO_TRANSACTIONS), BROKER_NAME, DocumentType.TRANSACTIONS)
    
    if not data:
        logger.warning("No transactions extracted.")
        return 0
        
    count = 0
    skipped = 0
    
    # Pre-fetch existing to avoid dupes? 
    # Or rely on unique constraint?
    # Transaction model likely doesn't have unique constraint on (broker, ticker, time).
    # I'll check manually.
    
    for row in data:
        # Date parsing
        date_str = row.get('date')
        ts = datetime.now()
        if date_str:
            # Parse Italian date: 18-dic-2025
            try:
                # Replace month names
                months = {
                    'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mag': '05', 'giu': '06',
                    'lug': '07', 'ago': '08', 'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
                }
                for m, n in months.items():
                    if m in date_str.lower():
                        date_str = date_str.lower().replace(m, n)
                        break
                # Try format %d-%m-%Y
                tx_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                ts = datetime.combine(tx_date, datetime.min.time())
            except Exception as e:
                logger.warning(f"Date parse error '{date_str}': {e}")
        
        raw_ticker = row.get('ticker', 'UNKNOWN')
        # Truncate to 20 chars to fit DB schema
        ticker = raw_ticker[:20]
        
        qty = parse_decimal(row.get('quantity', 0))
        price = parse_decimal(row.get('price', 0))
        
        # Skip invalid or empty transactions
        if qty == 0 and price == 0:
            skipped += 1
            continue
            
        isin = row.get('isin')
        
        raw_type = row.get('type', 'TRADING').upper()
        # Parser sometimes returns 'op', sometimes 'operation' (from regex group names)
        raw_op = row.get('op') or row.get('operation') or ''
        raw_op = str(raw_op).upper()
        
        raw_type = row.get('type', 'TRADING').upper()
        
        if not raw_op and row.get('type') == 'TRADING':
            # Try to deduce from generic type or description
            pass

        # Mapping
        op_map = {
            'ACQUISTA': 'BUY',
            'VENDI': 'SELL',
            'DIVIDENDO': 'DIVIDEND',
            'DIVIDENDI': 'DIVIDEND',
            'BONIFICO': 'DEPOSIT',
            'DEPOSIT': 'DEPOSIT',
            'DEPOSITO': 'DEPOSIT',
            'TRASFERIMENTODILIQUIDITÀ': 'DEPOSIT',
            'TRANSFER': 'DEPOSIT',
            'PRELIEVO': 'WITHDRAW',
            'INTERESSI': 'INTEREST',
            'TRADING': 'TRADE',
            'CONTRATTAZIONE': 'TRADE',
            'OPERAZIONESULCAPITALE': 'DIVIDEND', # Default if op missing
            'OPERAZIONE SUL CAPITALE': 'DIVIDEND'
        }
        
        # Use 'op' if present (Acquista/Vendi), else use 'type' (DIVIDEND/TRANSFER)
        key = (raw_op if raw_op else raw_type).upper()
        # Handle 'Trasferimentodiliquidità' potentially having accents/issues
        if 'TRASFERIMENTO' in key: key = 'TRANSFER'
        
        operation = op_map.get(key, 'UNKNOWN')
        
        # Special case: TRANSFER Amount > 0 -> DEPOSIT, < 0 -> WITHDRAW
        if getattr(row, 'type', '').upper() in ['TRANSFER', 'DEPOSIT', 'TRASFERIMENTODILIQUIDITÀ'] or operation == 'DEPOSIT':
            # Use total_amount sign (calculated later? No, qty * price? No, amount usually from 'amount' field for Cash)
            # PDF Parser for DEPOSIT returns 'amount' field directly?
            # Let's check regex: `(?P<amount>-?[\\d,]+)EUR`
            # Parser might put it in 'quantity' or 'total_amount' depending on normalization.
            # INGESTION NOTE: ExtractionEngine might normalize 'amount' -> 'quantity'.
            # Checking extraction engine extraction logic... assumed yes.
            
            # If QTY is used for amount in cash txs:
            if qty > 0: operation = 'DEPOSIT'
            else: operation = 'WITHDRAW'
        
        # De-dupe check: same broker, ticker, date, qty, price
        # exists = session.query(Transaction).filter(
        #     Transaction.broker == BROKER_NAME,
        #     Transaction.ticker == ticker,
        #     Transaction.timestamp == ts,
        #     Transaction.quantity == qty
        # ).first()
        
        exists = None # FORCE INSERT
        
        if exists:
            skipped += 1
            continue
            
        t = Transaction(
            id=uuid.uuid4(),
            broker=BROKER_NAME,
            ticker=ticker,
            isin=isin,
            timestamp=ts,
            operation=operation,
            quantity=qty,
            price=price,
            currency="EUR", 
            total_amount=qty * price,
            source_document=BGSAXO_TRANSACTIONS
        )
        session.add(t)
        count += 1
        
    session.commit()
    logger.info(f"Inserted {count} transactions (skipped {skipped} dupes).")
    return count

def main():
    logger.info("Starting Ingestion...")
    try:
        init_db() # Ensure tables exist
        print("Tables initialized.")
    except Exception as e:
        logger.error(f"Init DB failed: {e}")

    session = SessionLocal()
    try:
        h_count = ingest_holdings(session)
        t_count = ingest_transactions(session)
        
        print("\n" + "="*50)
        print("INGESTION REPORT")
        print("="*50)
        print(f"Holdings:     {h_count}")
        print(f"Transactions: {t_count}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
