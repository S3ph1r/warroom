"""
Debug Tesla History
List all transactions for Tesla (US88160R1014) to pinpoint where the extra quantity comes from.
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction

def debug_tesla():
    session = SessionLocal()
    try:
        # Search by ISIN or Name
        txs = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL",
            (Transaction.isin == "US88160R1014") | (Transaction.ticker.like("%TESLA%"))
        ).order_by(Transaction.timestamp).all()
        
        print(f"Found {len(txs)} transactions for Tesla in Scalable Capital:")
        print(f"{'DATE':<12} | {'OP':<10} | {'QTY':>8} | {'PRICE':>8} | {'DOC':<30}")
        print("-" * 80)
        
        total_qty = Decimal(0)
        
        for tx in txs:
            print(f"{tx.timestamp:<20} | {tx.operation:<10} | {tx.quantity:>8.4f} | {tx.price:>8.2f} | AMT: {tx.total_amount:>8.2f} | DOC: {tx.source_document}")
            
            if tx.operation == "BUY" or tx.operation == "CORRECTION_INC":
                total_qty += tx.quantity
            elif tx.operation == "SELL" or tx.operation == "CORRECTION_DEC":
                total_qty -= tx.quantity
            elif tx.operation.startswith("CORRECTION") and tx.quantity < 0:
                 # Just in case quantity is negative in DB (it shouldn't be, usually positive values with Op indicating direction)
                 total_qty += tx.quantity
                 
        print("-" * 80)
        print(f"CALCULATED TOTAL: {total_qty}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_tesla()
