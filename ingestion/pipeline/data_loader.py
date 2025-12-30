"""
IDP Pipeline - Module D: Data Loader
Normalizes data and loads into SQLite database.
"""
import sys
import re
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Any
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# NORMALIZATION UTILITIES
# =============================================================================

def parse_european_number(value: Any) -> Optional[Decimal]:
    """
    Parse European format numbers: 1.234,56 -> 1234.56
    Also handles: 1,234.56 (US format) and plain numbers.
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    
    s = str(value).strip()
    if not s or s == '-':
        return None
    
    # Remove currency symbols/text
    s = re.sub(r'[€$£EUR USD]', '', s).strip()
    
    # Count separators
    dots = s.count('.')
    commas = s.count(',')
    
    if dots > 0 and commas > 0:
        # Mixed separators
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        
        if last_comma > last_dot:
            # European: 1.234,56
            s = s.replace('.', '').replace(',', '.')
        else:
            # US: 1,234.56
            s = s.replace(',', '')
    elif commas == 1 and dots == 0:
        # Assume European decimal: 123,45
        s = s.replace(',', '.')
    elif dots == 1 and commas == 0:
        # Already standard: 123.45
        pass
    else:
        # Multiple of same separator: assume thousands
        if dots > 1:
            s = s.replace('.', '')
        elif commas > 1:
            s = s.replace(',', '')
    
    try:
        return Decimal(s)
    except InvalidOperation:
        logger.warning(f"Could not parse number: {value}")
        return None


def parse_date(value: Any) -> Optional[date]:
    """
    Parse various date formats to date object.
    Handles: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD-MMM-YYYY
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, date):
        return value
    
    s = str(value).strip()
    if not s:
        return None
    
    # Italian month names
    month_map = {
        'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
        'set': '09', 'ott': '10', 'nov': '11', 'dic': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }
    
    formats = [
        '%Y-%m-%d',      # 2025-12-29
        '%d/%m/%Y',      # 29/12/2025
        '%d-%m-%Y',      # 29-12-2025
        '%d.%m.%Y',      # 29.12.2025
        '%Y/%m/%d',      # 2025/12/29
    ]
    
    # Try standard formats
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    
    # Try MMM format (e.g., 29-dic-2025)
    match = re.match(r'(\d{1,2})-([a-zA-Z]{3})-(\d{4})', s)
    if match:
        day, month_str, year = match.groups()
        month = month_map.get(month_str.lower())
        if month:
            return date(int(year), int(month), int(day))
    
    logger.warning(f"Could not parse date: {value}")
    return None


def normalize_operation(value: str) -> str:
    """Normalize operation type to standard values."""
    v = str(value).upper().strip()
    
    mapping = {
        'ACQUISTA': 'BUY', 'BUY': 'BUY', 'ACQUISTO': 'BUY', 'COMPRA': 'BUY',
        'VENDI': 'SELL', 'SELL': 'SELL', 'VENDITA': 'SELL', 'VENDUTO': 'SELL',
        'DIVIDENDO': 'DIVIDEND', 'DIVIDEND': 'DIVIDEND', 'DIVIDENDOINCONTANTI': 'DIVIDEND',
        'COMMISSIONE': 'FEE', 'FEE': 'FEE', 'FEES': 'FEE',
        'DEPOSITO': 'DEPOSIT', 'DEPOSIT': 'DEPOSIT', 'VERSAMENTO': 'DEPOSIT',
        'PRELIEVO': 'WITHDRAW', 'WITHDRAW': 'WITHDRAW', 'WITHDRAWAL': 'WITHDRAW',
        'INTERESSI': 'INTEREST', 'INTEREST': 'INTEREST',
    }
    
    for key, normalized in mapping.items():
        if key in v:
            return normalized
    
    return 'OTHER'


def normalize_asset_type(value: str) -> str:
    """Normalize asset type to standard values."""
    v = str(value).upper().strip()
    
    mapping = {
        'STOCK': 'STOCK', 'AZIONE': 'STOCK', 'AZIONI': 'STOCK', 'EQUITY': 'STOCK',
        'ETF': 'ETF', 'ETP': 'ETF', 'UCITS': 'ETF',
        'BOND': 'BOND', 'OBBLIGAZIONE': 'BOND', 'OBBLIGAZIONI': 'BOND',
        'CRYPTO': 'CRYPTO', 'CRYPTOCURRENCY': 'CRYPTO',
        'COMMODITY': 'COMMODITY', 'COMMODITIES': 'COMMODITY', 'MATERIE PRIME': 'COMMODITY',
        'FUND': 'FUND', 'FONDO': 'FUND', 'FONDI': 'FUND',
        'CASH': 'CASH', 'LIQUIDITA': 'CASH', 'LIQUIDITÀ': 'CASH',
    }
    
    for key, normalized in mapping.items():
        if key in v:
            return normalized
    
    return 'STOCK'  # Default


def validate_isin(value: str) -> Optional[str]:
    """Validate and clean ISIN code."""
    if not value:
        return None
    
    s = str(value).upper().strip()
    
    # ISIN pattern: 2 letters + 10 alphanumeric
    if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', s):
        return s
    
    return None


# =============================================================================
# DATA LOADER
# =============================================================================

class DataLoader:
    """
    Loads normalized data into the database.
    Implements UPSERT logic for Holdings and duplicate detection for Transactions.
    """
    
    def __init__(self):
        self.stats = {
            'holdings_created': 0,
            'holdings_updated': 0,
            'transactions_created': 0,
            'transactions_skipped': 0,
            'errors': 0
        }
    
    def load_holdings(
        self, 
        broker: str, 
        items: List[Dict], 
        source_file: str,
        snapshot_date: Optional[date] = None
    ) -> int:
        """
        Load holdings into database with UPSERT logic.
        Deletes existing holdings for this broker before inserting new ones.
        
        Returns:
            Number of records inserted
        """
        if not items:
            logger.warning("No holdings to load")
            return 0
        
        snapshot_date = snapshot_date or date.today()
        
        session = SessionLocal()
        count = 0
        
        try:
            # Clear existing holdings for this broker
            existing = session.query(Holding).filter(Holding.broker == broker).count()
            if existing > 0:
                logger.info(f"   Deleting {existing} existing holdings for {broker}")
                session.query(Holding).filter(Holding.broker == broker).delete()
            
            # Insert new holdings
            for item in items:
                try:
                    holding = Holding(
                        id=uuid.uuid4(),
                        broker=broker,
                        ticker=item.get('ticker', 'UNKNOWN'),
                        isin=validate_isin(item.get('isin', '')),
                        name=item.get('name', item.get('ticker', '')),
                        asset_type=normalize_asset_type(item.get('asset_type', 'STOCK')),
                        quantity=parse_european_number(item.get('quantity', 0)) or Decimal('0'),
                        purchase_price=parse_european_number(item.get('purchase_price')),
                        current_price=parse_european_number(item.get('current_price')),
                        current_value=parse_european_number(item.get('current_value', 0)) or Decimal('0'),
                        currency=item.get('currency', 'EUR'),
                        source_document=source_file,
                        last_updated=datetime.now()
                    )
                    session.add(holding)
                    count += 1
                    
                except Exception as e:
                    logger.error(f"   Error adding holding: {e}")
                    self.stats['errors'] += 1
            
            session.commit()
            self.stats['holdings_created'] = count
            logger.info(f"   ✅ Inserted {count} holdings for {broker}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"   ❌ Database error: {e}")
            count = 0
            
        finally:
            session.close()
        
        return count
    
    def load_transactions(
        self, 
        broker: str, 
        items: List[Dict], 
        source_file: str
    ) -> int:
        """
        Load transactions into database with duplicate detection.
        Skips transactions that already exist based on key fields.
        
        Returns:
            Number of new records inserted
        """
        if not items:
            logger.warning("No transactions to load")
            return 0
        
        session = SessionLocal()
        inserted = 0
        skipped = 0
        
        try:
            for item in items:
                try:
                    # Build transaction
                    tx_date = parse_date(item.get('date'))
                    ticker = item.get('ticker', 'UNKNOWN')
                    operation = normalize_operation(item.get('operation', 'OTHER'))
                    quantity = parse_european_number(item.get('quantity', 0)) or Decimal('0')
                    price = parse_european_number(item.get('price', 0)) or Decimal('0')
                    total = parse_european_number(item.get('total_amount', 0)) or Decimal('0')
                    
                    # Check for duplicate (same broker, date, ticker, operation, amount)
                    if tx_date:
                        existing = session.query(Transaction).filter(
                            Transaction.broker == broker,
                            Transaction.ticker == ticker,
                            Transaction.operation == operation,
                            Transaction.total_amount == total
                        ).first()
                        
                        if existing:
                            skipped += 1
                            continue
                    
                    # Insert new transaction
                    tx = Transaction(
                        id=uuid.uuid4(),
                        broker=broker,
                        ticker=ticker,
                        isin=validate_isin(item.get('isin', '')),
                        operation=operation,
                        status='COMPLETED',
                        quantity=quantity,
                        price=price,
                        total_amount=total,
                        currency=item.get('currency', 'EUR'),
                        fees=parse_european_number(item.get('fees', 0)) or Decimal('0'),
                        timestamp=datetime.combine(tx_date, datetime.min.time()) if tx_date else datetime.now(),
                        source_document=source_file,
                    )
                    session.add(tx)
                    inserted += 1
                    
                except Exception as e:
                    logger.error(f"   Error adding transaction: {e}")
                    self.stats['errors'] += 1
            
            session.commit()
            self.stats['transactions_created'] = inserted
            self.stats['transactions_skipped'] = skipped
            
            logger.info(f"   ✅ Inserted {inserted} transactions, skipped {skipped} duplicates")
            
        except Exception as e:
            session.rollback()
            logger.error(f"   ❌ Database error: {e}")
            inserted = 0
            
        finally:
            session.close()
        
        return inserted
    
    def log_import(
        self, 
        broker: str, 
        filename: str, 
        file_path: str,
        holdings_count: int,
        transactions_count: int,
        status: str = 'SUCCESS',
        errors: Optional[dict] = None
    ):
        """Log the import operation."""
        session = SessionLocal()
        
        try:
            import_log = ImportLog(
                id=uuid.uuid4(),
                broker=broker,
                filename=filename,
                file_path=file_path,
                holdings_created=holdings_count,
                transactions_created=transactions_count,
                status=status,
                errors=errors
            )
            session.add(import_log)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log import: {e}")
            
        finally:
            session.close()
    
    def get_stats(self) -> dict:
        """Return loader statistics."""
        return self.stats.copy()
