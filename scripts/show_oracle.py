
import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.getcwd())

from db.database import get_db
from db.models import Holding
from sqlalchemy import select

def show_oracle_data():
    db = next(get_db())
    print("--- ORACLE CHECK (Holdings Table) ---")
    print(f"{'Broker':<15} | {'Ticker':<8} | {'Qty':>8} | {'Purch Price':>12} | {'Cost Basis':>12}")
    
    holdings = db.scalars(select(Holding)).all()
    
    targets = ['RACE', 'XAU', 'XAG', 'PYPL', 'NVDA']
    
    for h in holdings:
        if h.ticker in targets or h.ticker == 'RACE.MI':
            pp = h.purchase_price if h.purchase_price else 0
            cost = h.quantity * pp
            print(f"{h.broker:<15} | {h.ticker:<8} | {h.quantity:>8.4f} | {pp:>12.4f} | {cost:>12.2f}")

if __name__ == "__main__":
    show_oracle_data()
