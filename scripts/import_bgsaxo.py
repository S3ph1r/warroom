#!/usr/bin/env python
"""
WAR ROOM - Import BG Saxo Positions to Database
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, init_db
from db.models import Transaction, AssetRegistry
from ingestion.parsers.bgsaxo_positions import BGSaxoPositionsParser
from loguru import logger


def import_positions_to_db(file_path: str, skip_existing: bool = True):
    """
    Import BG Saxo positions CSV to database.
    
    Args:
        file_path: Path to the CSV file
        skip_existing: If True, skip assets that already exist in database
    """
    logger.info(f"🎯 Importing BG Saxo positions from: {file_path}")
    
    # Parse CSV
    parser = BGSaxoPositionsParser(file_path)
    parser.parse()
    
    # Get summary
    summary = parser.get_summary()
    logger.info(f"📊 Found {summary['total_positions']} positions")
    logger.info(f"💰 Total Market Value: €{summary['total_market_value_eur']:,.2f}")
    logger.info(f"📈 Total P&L: €{summary['total_pnl_eur']:,.2f}")
    
    # Connect to database
    db = SessionLocal()
    
    try:
        # Import assets
        assets = parser.to_asset_registry()
        assets_added = 0
        assets_skipped = 0
        
        for asset_data in assets:
            # Skip if ticker is empty or None
            if not asset_data.get('ticker'):
                logger.warning(f"Skipping asset with empty ticker: {asset_data.get('name', 'Unknown')}")
                assets_skipped += 1
                continue
            
            # Check if asset exists
            existing = db.query(AssetRegistry).filter(
                AssetRegistry.ticker == asset_data['ticker']
            ).first()
            
            if existing:
                assets_skipped += 1
                continue
            
            try:
                asset = AssetRegistry(
                    ticker=asset_data['ticker'],
                    isin=asset_data['isin'] if asset_data.get('isin') else None,
                    name=asset_data['name'][:255] if asset_data.get('name') else asset_data['ticker'],
                    asset_class=asset_data.get('asset_class', 'STOCK'),
                    currency=asset_data.get('currency', 'EUR'),
                    exchange=asset_data.get('exchange'),
                    watch_level=asset_data.get('watch_level', 1),
                )
                db.add(asset)
                db.flush()  # Flush to catch errors immediately
                assets_added += 1
            except Exception as e:
                logger.warning(f"Error adding asset {asset_data['ticker']}: {e}")
                db.rollback()
                assets_skipped += 1
        
        db.commit()
        logger.info(f"✅ Assets: {assets_added} added, {assets_skipped} skipped")
        
        # Import transactions (positions converted to BUY transactions)
        transactions = parser.to_transactions()
        tx_added = 0
        tx_skipped = 0
        
        for tx_data in transactions:
            # Check for duplicate (same ticker, quantity, date)
            existing = db.query(Transaction).filter(
                Transaction.ticker_symbol == tx_data['ticker_symbol'],
                Transaction.quantity == tx_data['quantity'],
                Transaction.platform == 'BG_SAXO',
            ).first()
            
            if existing and skip_existing:
                tx_skipped += 1
                continue
            
            if not existing:
                tx = Transaction(
                    timestamp=tx_data['timestamp'] or datetime.now(),
                    ticker_symbol=tx_data['ticker_symbol'],
                    isin=tx_data['isin'],
                    platform=tx_data['platform'],
                    operation_type=tx_data['operation_type'],
                    quantity=tx_data['quantity'],
                    price_unit=tx_data['price_unit'],
                    fiat_amount=tx_data['fiat_amount'],
                    currency_original=tx_data['currency_original'],
                    status=tx_data['status'],
                    notes=tx_data['notes'],
                    csv_source=Path(file_path).name,
                )
                db.add(tx)
                tx_added += 1
        
        db.commit()
        logger.info(f"✅ Transactions: {tx_added} added, {tx_skipped} skipped")
        
        logger.info("🚀 Import completed successfully!")
        
        return {
            'assets_added': assets_added,
            'assets_skipped': assets_skipped,
            'transactions_added': tx_added,
            'transactions_skipped': tx_skipped,
        }
        
    except Exception as e:
        logger.error(f"❌ Error importing: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default to latest BG Saxo file
        file_path = "D:/Download/BGSAXO/Posizioni_19-dic-2025_17_49_12.csv"
    
    if not Path(file_path).exists():
        logger.error(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    import_positions_to_db(file_path)


if __name__ == "__main__":
    main()
