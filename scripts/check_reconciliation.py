import sys
import logging
from pathlib import Path
from decimal import Decimal
from sqlalchemy import func

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Holding, Transaction

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Reconcile")

def check_reconciliation():
    session = SessionLocal()
    
    logger.info("==========================================")
    logger.info("      RECONCILIATION CHECK (BG_SAXO)      ")
    logger.info("==========================================")
    
    # 1. Fetch Holdings
    holdings = session.query(Holding).filter(Holding.broker == "BG_SAXO").all()
    logger.info(f"Total Holdings: {len(holdings)}")
    
    # 2. Fetch Transactions Summary
    # Group by Ticker/ISIN and sum quantity
    # Note: We use ISIN as primary key if available, else Ticker
    
    # We'll pull all transactions and aggregate in python to handle fuzzy matching if needed
    transactions = session.query(Transaction).filter(Transaction.broker == "BG_SAXO").all()
    logger.info(f"Total Transactions: {len(transactions)}")
    
    # Build Map: Key -> Net Quantity
    txn_map = {}
    
    for t in transactions:
        # Key: Prefer ISIN, fallback to Ticker (cleaned)
        key = t.isin if t.isin else t.ticker
        if not key:
            continue
            
        qty = t.quantity or Decimal(0)
        if t.operation == 'SELL':
            qty = -qty
        
        # Only sum BUY/SELL (ignore Dividends/Deposits for quantity check)
        if t.operation in ['BUY', 'SELL']:
             txn_map[key] = txn_map.get(key, Decimal(0)) + qty

    # 3. Compare
    logger.info("\n--- MISMATCH REPORT ---")
    matches = 0
    mismatches = 0
    missing_in_txn = 0
    
    for h in holdings:
        h_key = h.isin if h.isin else h.ticker
        
        # Look for match in transactions
        # Try exact ISIN
        t_qty = txn_map.get(h_key)
        
        # If not found and we have an ISIN, try looking up by Ticker just in case
        if t_qty is None and h.isin:
             t_qty = txn_map.get(h.ticker)
             
        if t_qty is None:
            logger.warning(f"[MISSING TXN] {h.name[:30]} | ISIN: {h.isin} | Ticker: {h.ticker} | Holding Qty: {h.quantity}")
            missing_in_txn += 1
            continue
            
        # Compare (allow small float diff)
        diff = abs(h.quantity - t_qty)
        if diff < 0.01:
            matches += 1
        else:
            logger.warning(f"[MISMATCH] {h.name[:30]} \t| H: {h.quantity:.2f} | T: {t_qty:.2f} | Diff: {diff:.2f} | Key: {h_key}")
            mismatches += 1

    logger.info("\n------------------------------------------")
    logger.info(f"PERFECT MATCHES: {matches}")
    logger.info(f"MISMATCHES:      {mismatches}")
    logger.info(f"MISSING IN TXN:  {missing_in_txn}")
    logger.info("------------------------------------------")
    
    session.close()

if __name__ == "__main__":
    check_reconciliation()
