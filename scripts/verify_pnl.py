
import sys
import os

# Add parent directory to path
sys.path.append(os.getcwd())

from db.database import get_db
from db.models import Transaction, Holding
from sqlalchemy import select, func

def verify_nic():
    db = next(get_db())
    print("--- Net Invested Capital Verification ---")
    
    # query sums
    deposits = db.query(func.sum(Transaction.total_amount)).filter(Transaction.operation == 'DEPOSIT').scalar() or 0
    withdrawals = db.query(func.sum(Transaction.total_amount)).filter(Transaction.operation == 'WITHDRAW').scalar() or 0
    balances = db.query(func.sum(Transaction.total_amount)).filter(Transaction.operation == 'BALANCE').scalar() or 0
    
    print(f"Total Deposits: {deposits:,.2f}")
    print(f"Total Withdrawals: {withdrawals:,.2f}")
    print(f"Total Balances (Initial Capital): {balances:,.2f}")
    
    nic = deposits + balances - withdrawals
    print(f"Net Invested Capital (NIC): {nic:,.2f}")
    
    # Compare with current Portfolio Value
    # (Approximation: sum of holdings * current_price if available, else purchase price)
    # Ideally should use build_portfolio_data logic, but let's just sum holdings cost basis vs value
    
    holdings = db.scalars(select(Holding)).all()
    # Note: Holding value in DB is snapshot, real-time value comes from API.
    # We will use what's in DB or just skip this comparison for now as it requires live prices.
    
    print("-" * 30)
    print("Logic check: NIC represents the TOTAL CASH INJECTED into the system.")
    print("True P&L = Current Value - NIC")
    
if __name__ == "__main__":
    verify_nic()
