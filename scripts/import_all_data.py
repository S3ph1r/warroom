"""
WAR ROOM - Data Import Service
Imports parsed transactions from all brokers into PostgreSQL database
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal, init_db
from db.models import Transaction, AssetRegistry, CSVImportLog
from ingestion.parsers import (
    parse_bgsaxo_positions,
    parse_bgsaxo_transactions_pdf,
    parse_scalable_pdf,
    parse_all_scalable_pdfs,
    parse_revolut_pdf,
    parse_trade_republic_pdf,
    parse_ibkr_csv,
    parse_binance_csv,
    parse_all_binance_csvs,
)


class DataImportService:
    """Service to import all parsed data into database"""
    
    def __init__(self):
        self.session = None
        self.stats = {
            'transactions_added': 0,
            'transactions_skipped': 0,
            'assets_added': 0,
            'errors': []
        }
    
    def connect(self):
        """Initialize database connection"""
        try:
            init_db()
            self.session = SessionLocal()
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.session:
            self.session.close()
    
    def import_transaction(self, tx: Dict, platform: str) -> bool:
        """Import a single transaction into database"""
        try:
            # Create unique identifier based on key fields
            timestamp = tx.get('timestamp')
            amount = tx.get('fiat_amount') or tx.get('net_amount') or Decimal('0')
            
            if not timestamp:
                return False
            
            # Get ticker
            ticker = tx.get('symbol') or tx.get('currency') or 'UNKNOWN'
            if ticker in ('-', ''):
                ticker = 'UNKNOWN'
            
            # Check for duplicate
            existing = self.session.query(Transaction).filter(
                Transaction.timestamp == timestamp,
                Transaction.platform == platform,
                Transaction.ticker_symbol == ticker
            ).first()
            
            if existing:
                self.stats['transactions_skipped'] += 1
                return False
            
            # Map operation type to valid DB values
            op_type = tx.get('operation_type', 'BUY')
            type_mapping = {
                'STAKING_REWARD': 'DIVIDEND',
                'AIRDROP': 'DIVIDEND',
                'RECEIVE': 'DEPOSIT',
                'SEND': 'WITHDRAW',
                'TRADE': 'BUY',
                'PAYMENT': 'WITHDRAW',
                'TRANSFER': 'DEPOSIT',
                'TAX': 'FEE',
                'ADJUSTMENT': 'FEE',
                'FOREX': 'FEE',
                'WITHDRAW_CASH': 'WITHDRAW',
                'CRYPTO_BUY': 'BUY',
                'CRYPTO_SELL': 'SELL',
                'INVESTMENT_BUY': 'BUY',
                'INVESTMENT_SELL': 'SELL',
            }
            op_type = type_mapping.get(op_type, op_type)
            
            # Ensure valid operation type
            valid_types = ('BUY', 'SELL', 'DIVIDEND', 'DEPOSIT', 'WITHDRAW', 'FEE', 'INTEREST')
            if op_type not in valid_types:
                op_type = 'BUY'
            
            # Calculate price_unit
            quantity = tx.get('quantity') or tx.get('amount') or Decimal('1')
            if quantity == 0:
                quantity = Decimal('1')
            price_unit = abs(amount / Decimal(str(quantity))) if quantity else Decimal('0')
            
            # Create transaction
            new_tx = Transaction(
                timestamp=timestamp,
                ticker_symbol=ticker[:20],  # Max 20 chars
                isin=tx.get('isin'),
                operation_type=op_type,
                quantity=abs(Decimal(str(quantity))) if quantity else Decimal('0'),
                price_unit=price_unit,
                fiat_amount=amount if amount else Decimal('0'),
                platform=platform,
                status='VERIFIED',
                notes=tx.get('description', '')[:500] if tx.get('description') else None
            )
            
            self.session.add(new_tx)
            self.stats['transactions_added'] += 1
            return True
            
        except Exception as e:
            self.stats['errors'].append(f"Import error: {str(e)[:100]}")
            return False
    
    def import_bgsaxo(self, processed_dir: str):
        """Import BG Saxo transactions and positions"""
        logger.info("Importing BG Saxo data...")
        
        dir_path = Path(processed_dir) / 'bgsaxo'
        if not dir_path.exists():
            logger.warning(f"BG Saxo directory not found: {dir_path}")
            return
        
        # Import positions CSV
        for csv_file in dir_path.glob('*.csv'):
            try:
                positions = parse_bgsaxo_positions(str(csv_file))
                for pos in positions:
                    # Convert position to transaction-like format
                    tx = {
                        'timestamp': pos.get('open_datetime') or datetime.now(),
                        'symbol': pos.get('ticker') or pos.get('name'),
                        'isin': pos.get('isin'),
                        'operation_type': 'BUY',
                        'quantity': pos.get('quantity'),
                        'fiat_amount': pos.get('invested_eur') or pos.get('original_value'),
                    }
                    self.import_transaction(tx, 'BG_SAXO')
            except Exception as e:
                logger.error(f"Error parsing {csv_file}: {e}")
        
        # Import transaction PDFs
        for pdf_file in dir_path.glob('*.pdf'):
            try:
                transactions = parse_bgsaxo_transactions_pdf(str(pdf_file))
                for tx in transactions:
                    self.import_transaction(tx, 'BG_SAXO')
            except Exception as e:
                logger.error(f"Error parsing {pdf_file}: {e}")
        
        self.session.commit()
        logger.info(f"BG Saxo import complete")
    
    def import_scalable_capital(self, processed_dir: str):
        """Import Scalable Capital transactions"""
        logger.info("Importing Scalable Capital data...")
        
        dir_path = Path(processed_dir) / 'scalable'
        if not dir_path.exists():
            logger.warning(f"Scalable Capital directory not found: {dir_path}")
            return
        
        try:
            transactions = parse_all_scalable_pdfs(str(dir_path))
            for tx in transactions:
                self.import_transaction(tx, 'SCALABLE_CAPITAL')
            self.session.commit()
        except Exception as e:
            logger.error(f"Error parsing Scalable Capital: {e}")
        
        logger.info(f"Scalable Capital import complete")
    
    def import_revolut(self, processed_dir: str):
        """Import Revolut transactions"""
        logger.info("Importing Revolut data...")
        
        dir_path = Path(processed_dir) / 'revolut'
        if not dir_path.exists():
            logger.warning(f"Revolut directory not found: {dir_path}")
            return
        
        for pdf_file in dir_path.glob('*.pdf'):
            try:
                transactions = parse_revolut_pdf(str(pdf_file))
                for tx in transactions:
                    self.import_transaction(tx, 'REVOLUT')
            except Exception as e:
                logger.error(f"Error parsing {pdf_file}: {e}")
        
        self.session.commit()
        logger.info(f"Revolut import complete")
    
    def import_trade_republic(self, processed_dir: str):
        """Import Trade Republic transactions"""
        logger.info("Importing Trade Republic data...")
        
        dir_path = Path(processed_dir) / 'traderepublic'
        if not dir_path.exists():
            logger.warning(f"Trade Republic directory not found: {dir_path}")
            return
        
        for pdf_file in dir_path.glob('*.pdf'):
            try:
                transactions = parse_trade_republic_pdf(str(pdf_file))
                for tx in transactions:
                    self.import_transaction(tx, 'TRADE_REPUBLIC')
            except Exception as e:
                logger.error(f"Error parsing {pdf_file}: {e}")
        
        self.session.commit()
        logger.info(f"Trade Republic import complete")
    
    def import_ibkr(self, processed_dir: str):
        """Import IBKR transactions"""
        logger.info("Importing IBKR data...")
        
        dir_path = Path(processed_dir) / 'ibkr'
        if not dir_path.exists():
            logger.warning(f"IBKR directory not found: {dir_path}")
            return
        
        for csv_file in dir_path.glob('*.csv'):
            try:
                transactions = parse_ibkr_csv(str(csv_file))
                for tx in transactions:
                    self.import_transaction(tx, 'IBKR')
            except Exception as e:
                logger.error(f"Error parsing {csv_file}: {e}")
        
        self.session.commit()
        logger.info(f"IBKR import complete")
    
    def import_binance(self, processed_dir: str):
        """Import Binance transactions"""
        logger.info("Importing Binance data...")
        
        dir_path = Path(processed_dir) / 'binance'
        if not dir_path.exists():
            logger.warning(f"Binance directory not found: {dir_path}")
            return
        
        try:
            transactions = parse_all_binance_csvs(str(dir_path))
            for tx in transactions:
                self.import_transaction(tx, 'BINANCE')
            self.session.commit()
        except Exception as e:
            logger.error(f"Error parsing Binance: {e}")
        
        logger.info(f"Binance import complete")
    
    def import_all(self, processed_dir: str):
        """Import all broker data"""
        logger.info("=" * 60)
        logger.info("Starting full data import...")
        logger.info("=" * 60)
        
        self.import_bgsaxo(processed_dir)
        self.import_scalable_capital(processed_dir)
        self.import_revolut(processed_dir)
        self.import_trade_republic(processed_dir)
        self.import_ibkr(processed_dir)
        self.import_binance(processed_dir)
        
        # Log is optional - skip if there's an issue
        try:
            log_entry = CSVImportLog(
                filename="full_import",
                platform="ALL",
                rows_processed=self.stats['transactions_added'] + self.stats['transactions_skipped'],
                rows_inserted=self.stats['transactions_added'],
                rows_matched=self.stats['transactions_skipped'],
                status='SUCCESS' if not self.stats['errors'] else 'PARTIAL'
            )
            self.session.add(log_entry)
        except Exception as e:
            logger.warning(f"Could not log import: {e}")
        self.session.commit()
        
        logger.info("=" * 60)
        logger.info("IMPORT COMPLETE")
        logger.info(f"  Transactions added: {self.stats['transactions_added']}")
        logger.info(f"  Transactions skipped: {self.stats['transactions_skipped']}")
        logger.info(f"  Errors: {len(self.stats['errors'])}")
        logger.info("=" * 60)
        
        return self.stats


def run_full_import():
    """Run full import from Google Drive processed folder"""
    # Get processed directory from environment or default
    processed_dir = os.getenv('PROCESSED_ROOT_PATH', 'G:/Il mio Drive/WAR_ROOM_DATA/processed')
    
    service = DataImportService()
    
    if not service.connect():
        logger.error("Cannot connect to database")
        return None
    
    try:
        stats = service.import_all(processed_dir)
        return stats
    finally:
        service.close()


if __name__ == "__main__":
    print("\n🎯 WAR ROOM Data Import Service")
    print("=" * 50)
    
    stats = run_full_import()
    
    if stats:
        print(f"\n✅ Import complete!")
        print(f"   Added: {stats['transactions_added']} transactions")
        print(f"   Skipped: {stats['transactions_skipped']} duplicates")
        if stats['errors']:
            print(f"   ⚠️ Errors: {len(stats['errors'])}")
