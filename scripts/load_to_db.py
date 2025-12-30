import sys
import json
import logging
from pathlib import Path
from decimal import Decimal

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.transaction_service import TransactionService
from db.database import SessionLocal
from db.models import Transaction, Holding

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_broker_history(broker_name):
    logger.info(f"💾 LOADING DB: {broker_name.upper()}")
    
    file_path = ROOT_DIR / "data" / "clean" / f"{broker_name}_history.json"
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    # Sort by Date ASC is crucial for replay
    history.sort(key=lambda x: x['date'])
    
    db = SessionLocal()
    service = TransactionService(db)
    
    try:
        # 1. PURGE EXISTING DATA FOR BROKER
        # To avoid duplicates on re-run.
        # DANGEROUS: Only do this if we are Full Syncing.
        # User said: "Le holdings sono la source of truth".
        # If we just insert, we duplicate. So Purge is needed for Ingestion Re-run.
        
        logger.info("   Deleting old records...")
        db.query(Transaction).filter(Transaction.broker == broker_name).delete()
        db.query(Holding).filter(Holding.broker == broker_name).delete()
        db.commit()
        
        # 2. REPLAY HISTORY
        logger.info(f"   Replaying {len(history)} transactions...")
        
        for i, tx in enumerate(history):
            raw_qty = float(tx.get('quantity', 0))
            raw_type = tx.get('type', 'BUY').upper()
            
            # Map Mode and fix Qty sign
            mode = "BUY"
            qty = abs(raw_qty)
            
            if "SELL" in raw_type or "VENDITA" in raw_type:
                mode = "SELL"
            elif "DEPOSIT" in raw_type:
                mode = "DEPOSIT"
            elif "WITHDRAW" in raw_type:
                mode = "WITHDRAW"
            elif "DIVIDEND" in raw_type:
                # Service doesn't explicitly handle DIVIDEND in create_transaction logic shown
                # It treats simple BUY/SELL/DEP/WITH.
                # Use BALANCE for now or extend service?
                # User script showed create_transaction handling 'DEPOSIT' affects cash.
                # Dividend is like a DEPOSIT of Cash.
                mode = "DEPOSIT" # Treat as Cash Inflow
                # But careful: Dividend usually has Ticker associated.
                # Service 'DEPOSIT' updates Cash via _get_or_create_cash_holding.
                pass
            elif "RECONCILIATION" in raw_type:
                # Treating as BALANCE ADJUSTMENT (Conceptually a BUY of stock with 0 cost?)
                # If quantity is positive -> BUY.
                if raw_qty >= 0:
                    mode = "BUY" 
                else:
                    mode = "SELL"
            
            # Construct Payload
            ticker_val = tx.get('ticker', 'UNKNOWN')
            if ticker_val and len(ticker_val) > 20:
                ticker_val = ticker_val[:20]

            # Validate ISIN (Must be 12 chars)
            isin_val = tx.get("isin")
            if isin_val and len(isin_val) != 12:
                # logger.warning(f"Skipping invalid ISIN '{isin_val}' for {ticker_val}")
                isin_val = None

            payload = {
                "date": tx.get('date'),
                "broker": broker_name,
                "ticker": ticker_val,
                "mode": mode,
                "quantity": qty,
                "price": tx.get('price', 0),
                "fees": 0, 
                "currency": tx.get('currency', 'EUR'),
                "status": "COMPLETED",
                "asset_type": "STOCK",
                "isin": isin_val
            }

            # Handle Dividends specially if needed, but for now map to Deposit
            if "DIVIDEND" in raw_type:
               # Dividends don't change stock quantity.
               # If we send mode=DEPOSIT with Ticker, Service update Cash?
               # Lines 101-104: "For cash movements... Ticker might be empty".
               # It ignores ticker and updates cash for currency.
               # PERFECT.
               mode = "DEPOSIT" 
               payload['mode'] = "DEPOSIT"
               payload['ticker'] = tx.get('currency') # Dummy ticker for cash
               payload['asset_type'] = "CASH"
               # Amount is total_amount
               amount = float(tx.get('total_amount', 0))
               # If amount is negative (tax?), handle? 
               if amount < 0:
                   payload['mode'] = "WITHDRAW"
                   payload['quantity'] = abs(amount)
               else:
                   payload['quantity'] = abs(amount)

            # Reconcilation / Buy / Sell
            else:
                # Normal Stock Op
                pass

            # Execute
            try:
                service.create_transaction(payload)
            except Exception as inner_e:
                logger.error(f"❌ Failed on Tx {i}: {payload}")
                logger.error(f"Error: {inner_e}")
                raise inner_e

            
            if i % 50 == 0:
                print(".", end="", flush=True)

        logger.info("\n✅ Load Complete.")
        
    except Exception as e:
        logger.error(f"❌ Error loading DB: {e}")
        db.rollback()
    finally:
        service.close()

if __name__ == "__main__":
    load_broker_history("bgsaxo")
