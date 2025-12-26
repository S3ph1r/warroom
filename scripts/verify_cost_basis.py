
import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.getcwd())

from db.database import get_db
from db.database import get_db
from db.models import Holding
from sqlalchemy import select

def verify_cost_basis():
    db = next(get_db())
    print("--- Cost Basis Verification ---")
    
    holdings = db.scalars(select(Holding)).all()
    
    total_cost_basis = Decimal(0)
    cash_total = Decimal(0)
    
    fx_rates = {"USD": 0.95, "EUR": 1.0, "GBP": 1.15} # Approx rates for verification
    
    for h in holdings:
        if h.asset_type == "CASH":
            rate = fx_rates.get(h.currency, 1.0)
            val = h.quantity * Decimal(rate)
            cash_total += val
            print(f"CASH: {h.quantity:,.2f} {h.currency} -> {val:,.2f} EUR")
        else:
            if h.purchase_price is None:
                print(f"WARNING: {h.ticker} has NO purchase price! Using 0.")
                cost = Decimal(0)
            else:
                cost = h.quantity * h.purchase_price
            total_cost_basis += cost
            print(f"{h.ticker}: {h.quantity} * {h.purchase_price} = {cost:,.2f}")
            
    print("-" * 30)
    print(f"Total Cost Basis (Assets): {total_cost_basis:,.2f}")
    print(f"Total Cash: {cash_total:,.2f}")
    
    # User Estimate: ~20k + ~3-4k (Binance) = ~24k.
    # If Total Cost Basis is around 24k, then this is the metric.
    
if __name__ == "__main__":
    verify_cost_basis()
