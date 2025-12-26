import sys
import os
from datetime import datetime
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

print(f"DEBUG: Project Root: {project_root}")
print(f"DEBUG: sys.path: {sys.path}")

# Import directly from root packages
try:
    from db.database import SessionLocal
    from db.models import Transaction, Holding
    print("DEBUG: Imports successful")
except ImportError as e:
    print(f"DEBUG: Import failed: {e}")
    # Fallback/Debug check
    if os.path.exists(os.path.join(project_root, "db")):
        print("DEBUG: 'db' directory exists")
        if os.path.exists(os.path.join(project_root, "db", "__init__.py")):
             print("DEBUG: 'db/__init__.py' exists")
        else:
             print("DEBUG: 'db/__init__.py' MISSING")
    raise e

def cleanup():
    db = SessionLocal()
    try:
        print("Starting cleanup of test data...")
        
        # 1. Revert BUY NVDA
        # Find the specific test transaction (recent)
        tx_buy = db.query(Transaction).filter(
            Transaction.broker == "IBKR", # or "IBKR" depending on exact string used in test
            Transaction.ticker == "NVDA",
            Transaction.operation == "BUY",
            Transaction.quantity == 10,
            Transaction.price == 100
        ).order_by(Transaction.timestamp.desc()).first()

        if tx_buy:
            print(f"Found BUY transaction: {tx_buy.id} - {tx_buy.timestamp}")
            
            # Revert Holding
            holding = db.query(Holding).filter(
                Holding.broker == tx_buy.broker,
                Holding.ticker == tx_buy.ticker
            ).first()
            
            if holding:
                holding.quantity -= tx_buy.quantity
                holding.current_value -= (tx_buy.quantity * tx_buy.price) # Approx revert
                if holding.quantity <= 0:
                    print(f"Deleting holding {holding.ticker} as qty is 0")
                    db.delete(holding)
                else:
                    print(f"Updated holding {holding.ticker}: Qty {holding.quantity}")
            
            # Revert Cash (Buy reduced cash, so we add it back? No, we are deleting the transaction history)
            # Wait, if we delete the transaction, we must undo its effect.
            # Buy Effect: Cash -1000. 
            # Undo Effect: Cash +1000.
            
            cash_holding = db.query(Holding).filter(
                Holding.broker == tx_buy.broker,
                Holding.asset_type == "CASH",
                Holding.currency == tx_buy.currency
            ).first()
            
            if cash_holding:
                cash_holding.quantity += (tx_buy.total_amount + tx_buy.fees)
                cash_holding.current_value = cash_holding.quantity
                print(f"Reverted Cash impact of BUY: +{tx_buy.total_amount}")

            db.delete(tx_buy)
            print("Deleted BUY transaction")
        else:
            print("No test BUY transaction found.")

        # 2. Revert DEPOSIT 10000
        tx_dep = db.query(Transaction).filter(
            Transaction.broker == "IBKR",
            Transaction.operation == "DEPOSIT",
            Transaction.quantity == 10000
        ).order_by(Transaction.timestamp.desc()).first()

        if tx_dep:
            print(f"Found DEPOSIT transaction: {tx_dep.id} - {tx_dep.timestamp}")
            
            # Revert Cash (Deposit added cash, so we remove it)
            # Deposit Effect: Cash +10000.
            # Undo Effect: Cash -10000.
            
            cash_holding = db.query(Holding).filter(
                Holding.broker == tx_dep.broker,
                Holding.asset_type == "CASH",
                Holding.currency == tx_dep.currency
            ).first()
             
            if cash_holding:
                cash_holding.quantity -= tx_dep.quantity
                cash_holding.current_value = cash_holding.quantity
                print(f"Reverted Cash impact of DEPOSIT: -{tx_dep.quantity}")
                
            db.delete(tx_dep)
            print("Deleted DEPOSIT transaction")
        else:
             print("No test DEPOSIT transaction found.")

        db.commit()
        print("Cleanup committed successfully.")
        
        # Invalidate cache
        snapshot = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data", "portfolio_snapshot.json")
        if os.path.exists(snapshot):
            os.remove(snapshot)
            print("Invalidated portfolio snapshot.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
