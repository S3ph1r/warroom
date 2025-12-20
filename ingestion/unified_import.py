"""
Unified Import Service
Integrates inbox scanner with all broker parsers for one-click import.
"""
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction
from ingestion.inbox_scanner import InboxScanner
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedImportService:
    """
    Unified service that integrates inbox scanning with broker-specific parsers.
    """
    
    def __init__(self, inbox_path: str, processed_path: str):
        self.scanner = InboxScanner(inbox_path, processed_path)
        self.session = None
    
    def import_bgsaxo_positions(self, file_path: Path) -> int:
        """Parse BG Saxo positions CSV and import to DB."""
        import csv
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                # Skip summary rows
                if not row.get('Simbolo') or row.get('Simbolo') in ['', 'Azioni', 'ETP']:
                    continue
                
                try:
                    # Parse European number format
                    value_str = row.get('Esposizione (EUR)', '0').replace('.', '').replace(',', '.')
                    qty_str = row.get('Quantità', '0').replace('.', '').replace(',', '.')
                    price_str = row.get('Prezzo Strumento', '0').replace('.', '').replace(',', '.')
                    
                    records.append({
                        'ticker': row.get('Simbolo', 'UNKNOWN'),
                        'name': row.get('Descrizione', ''),
                        'quantity': Decimal(qty_str) if qty_str else Decimal('0'),
                        'price': Decimal(price_str) if price_str else Decimal('0'),
                        'value': Decimal(value_str) if value_str else Decimal('0'),
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping row: {e}")
        
        # Insert into DB
        return self._insert_positions('BG_SAXO', records)
    
    def import_scalable_status(self, file_path: Path) -> int:
        """Parse Scalable Capital Financial Status PDF."""
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install pymupdf")
            return 0
        
        records = []
        pdf = fitz.open(str(file_path))
        
        for page in pdf:
            text = page.get_text()
            lines = text.split('\n')
            
            # Look for position lines: "QTY\nTicker\nISIN\nVALUE EUR"
            i = 0
            while i < len(lines) - 3:
                line = lines[i].strip()
                
                # Check if line starts with a number (quantity)
                if line and line.replace('.', '').replace(',', '').isdigit():
                    try:
                        qty = Decimal(line.replace('.', '').replace(',', '.'))
                        ticker = lines[i + 1].strip()
                        isin = lines[i + 2].strip() if 'IE' in lines[i + 2] or 'US' in lines[i + 2] or 'DE' in lines[i + 2] or 'KY' in lines[i + 2] else ''
                        
                        # Look for value
                        for j in range(i + 3, min(i + 6, len(lines))):
                            if 'EUR' in lines[j]:
                                value_str = lines[j].replace('EUR', '').replace('.', '').replace(',', '.').strip()
                                try:
                                    value = Decimal(value_str)
                                    records.append({
                                        'ticker': ticker,
                                        'isin': isin,
                                        'quantity': qty,
                                        'value': value,
                                        'price': value / qty if qty else Decimal('0')
                                    })
                                except:
                                    pass
                                break
                    except:
                        pass
                i += 1
        
        pdf.close()
        return self._insert_positions('SCALABLE_CAPITAL', records)
    
    def import_binance_statement(self, file_path: Path, password: str = '66666666') -> int:
        """Parse Binance Account Statement PDF."""
        try:
            import fitz
        except ImportError:
            return 0
        
        records = []
        
        try:
            pdf = fitz.open(str(file_path))
            if pdf.is_encrypted:
                pdf.authenticate(password)
            
            for page in pdf:
                text = page.get_text()
                
                # Look for "Spot Account" section with holdings
                if 'Spot Account' in text or 'Holdings' in text:
                    lines = text.split('\n')
                    
                    for i, line in enumerate(lines):
                        # Pattern: SYMBOL QUANTITY VALUE
                        parts = line.split()
                        if len(parts) >= 2:
                            symbol = parts[0]
                            # Check if it's a crypto symbol
                            if symbol in ['BTC', 'ETH', 'BNB', 'USDT', 'USDC', 'SOL', 'XRP', 'ADA', 'DOT']:
                                try:
                                    qty = Decimal(parts[1].replace(',', ''))
                                    value = Decimal(parts[2].replace(',', '').replace('$', '')) if len(parts) > 2 else Decimal('0')
                                    records.append({
                                        'ticker': symbol,
                                        'quantity': qty,
                                        'value': value,
                                        'price': value / qty if qty else Decimal('0')
                                    })
                                except:
                                    pass
            
            pdf.close()
        except Exception as e:
            logger.error(f"Error parsing Binance PDF: {e}")
        
        return self._insert_positions('BINANCE', records)
    
    def import_revolut_trading(self, file_path: Path) -> int:
        """Parse Revolut Trading Account Statement PDF."""
        try:
            import fitz
        except ImportError:
            return 0
        
        records = []
        pdf = fitz.open(str(file_path))
        
        for page in pdf:
            text = page.get_text()
            
            # Look for Portfolio breakdown section
            if 'Portfolio breakdown' in text:
                lines = text.split('\n')
                
                # Find position entries
                for i, line in enumerate(lines):
                    # Pattern: SYMBOL Company ISIN QTY PRICE VALUE %
                    if line.startswith('US') or line.startswith('KY'):
                        # This is an ISIN, previous lines have symbol/company
                        try:
                            symbol = lines[i - 2].strip() if i >= 2 else ''
                            isin = line.strip()
                            
                            # Next lines have qty, price, value
                            qty_line = lines[i + 1] if i + 1 < len(lines) else '0'
                            price_line = lines[i + 2] if i + 2 < len(lines) else '0'
                            value_line = lines[i + 3] if i + 3 < len(lines) else '0'
                            
                            qty = Decimal(qty_line.replace(',', ''))
                            price = Decimal(price_line.replace('US$', '').replace(',', ''))
                            value = Decimal(value_line.replace('US$', '').replace(',', ''))
                            
                            records.append({
                                'ticker': symbol,
                                'isin': isin,
                                'quantity': qty,
                                'price': price,
                                'value': value
                            })
                        except:
                            pass
        
        pdf.close()
        return self._insert_positions('REVOLUT', records)
    
    def import_ibkr_csv(self, file_path: Path) -> int:
        """Parse IBKR transactions CSV."""
        import csv
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            for row in reader:
                if len(row) < 10 or row[0] != 'Transaction History' or row[1] != 'Data':
                    continue
                
                try:
                    # IBKR CSV format
                    date_str = row[2]
                    description = row[4]
                    tx_type = row[5]
                    symbol = row[6]
                    qty = Decimal(row[7]) if row[7] and row[7] != '-' else Decimal('0')
                    price = Decimal(row[8]) if row[8] and row[8] != '-' else Decimal('0')
                    amount = Decimal(row[9]) if row[9] else Decimal('0')
                    
                    if symbol and symbol != '-':
                        records.append({
                            'ticker': symbol,
                            'quantity': abs(qty),
                            'price': price,
                            'value': abs(amount),
                            'type': tx_type
                        })
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping IBKR row: {e}")
        
        return self._insert_positions('IBKR', records)
    
    def _insert_positions(self, platform: str, records: list) -> int:
        """Insert position records into database."""
        if not records:
            return 0
        
        session = SessionLocal()
        count = 0
        
        try:
            for rec in records:
                tx = Transaction(
                    id=uuid.uuid4(),
                    timestamp=datetime.now(),
                    ticker_symbol=rec.get('ticker', 'UNKNOWN'),
                    isin=rec.get('isin'),
                    platform=platform,
                    operation_type='BUY',  # Snapshot position
                    quantity=rec.get('quantity', Decimal('0')),
                    price_unit=rec.get('price', Decimal('0')),
                    fiat_amount=rec.get('value', Decimal('0')),
                    currency_original='EUR',
                    status='VERIFIED',
                    notes=f'Imported from inbox at {datetime.now().isoformat()}'
                )
                session.add(tx)
                count += 1
            
            session.commit()
            logger.info(f"Inserted {count} records for {platform}")
        
        except Exception as e:
            session.rollback()
            logger.error(f"Database insert failed: {e}")
            count = 0
        
        finally:
            session.close()
        
        return count
    
    def run_import(self, clear_existing: bool = True) -> dict:
        """
        Run full import workflow.
        
        Args:
            clear_existing: If True, clear existing data for imported brokers
        
        Returns:
            Import summary
        """
        pending = self.scanner.scan_inbox()
        results = {
            'timestamp': datetime.now().isoformat(),
            'brokers_processed': [],
            'total_records': 0,
            'errors': []
        }
        
        for broker, files in pending.items():
            for file_path in files:
                try:
                    count = 0
                    
                    if broker == 'bgsaxo':
                        count = self.import_bgsaxo_positions(file_path)
                    elif broker == 'scalable':
                        count = self.import_scalable_status(file_path)
                    elif broker == 'binance':
                        count = self.import_binance_statement(file_path)
                    elif broker == 'revolut':
                        count = self.import_revolut_trading(file_path)
                    elif broker == 'ibkr':
                        count = self.import_ibkr_csv(file_path)
                    elif broker == 'traderepublic':
                        logger.info(f"Trade Republic requires manual entry from screenshot")
                        continue
                    
                    results['brokers_processed'].append({
                        'broker': broker,
                        'file': file_path.name,
                        'records': count
                    })
                    results['total_records'] += count
                    
                    # Move to processed
                    self.scanner._move_to_processed(broker, file_path)
                    self.scanner._update_import_log(broker, file_path.name, count)
                    
                except Exception as e:
                    results['errors'].append({
                        'broker': broker,
                        'file': file_path.name,
                        'error': str(e)
                    })
        
        return results


def main():
    """CLI entry point."""
    import os
    
    inbox_path = os.getenv('INBOX_ROOT_PATH', 'G:/Il mio Drive/WAR_ROOM_DATA/inbox')
    processed_path = os.getenv('PROCESSED_ROOT_PATH', 'G:/Il mio Drive/WAR_ROOM_DATA/processed')
    
    service = UnifiedImportService(inbox_path, processed_path)
    
    print("=" * 60)
    print("🚀 UNIFIED IMPORT SERVICE")
    print("=" * 60)
    
    # Show status first
    service.scanner.print_status()
    
    # Ask for confirmation
    response = input("\nProceed with import? (y/n): ")
    if response.lower() == 'y':
        results = service.run_import()
        
        print("\n" + "=" * 60)
        print("📊 IMPORT RESULTS")
        print("=" * 60)
        
        for item in results['brokers_processed']:
            print(f"✅ {item['broker']}: {item['records']} records from {item['file']}")
        
        if results['errors']:
            print("\n❌ Errors:")
            for err in results['errors']:
                print(f"   {err['broker']}: {err['error']}")
        
        print(f"\n📈 Total: {results['total_records']} records imported")


if __name__ == "__main__":
    main()
