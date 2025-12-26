
import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.getcwd())

from db.database import get_db
from db.models import Holding
from sqlalchemy import select

# TARGET PRICES (EUR)
# Ticker -> New Purchase Price
# If tuple (total_cost, is_total), we calculate unit price.
PATCH_MAP = {
    "RACE": 444.00,       # Ferrari (TR)
    "ASML": 707.00,       # ASML (Saxo)
    "XAU": (420.00, True), # Gold (Revolut) - Total Cost 420
    "XAG": 56.00,         # Silver (Keep existing or update if known) - Skipping for now
    "RBOE": 13.47,        # iShares Automation (RBOT in DB?) - Check RBOT too
    "RBOT": 13.47,        # Alias
    "HO": 253.00,         # Thales
    "AFX": 52.13,         # Carl Zeiss (Avg of 1@58.8, 2@48.8)
    "BABA": 10.46,        # Alibaba (2RR)
    "AHLA": 10.46,        # Alibaba Alias
    "2RR": 10.46          # Alibaba Alias
}

def patch_db():
    db = next(get_db())
    print("--- Patching Cost Basis ---")
    
    holdings = db.scalars(select(Holding).where(Holding.quantity > 0)).all()
    count = 0
    
    for h in holdings:
        ticker_key = h.ticker.upper().split('.')[0] # Simple match first
        
        target = PATCH_MAP.get(ticker_key)
        if not target:
            target = PATCH_MAP.get(h.ticker.upper()) # Try full match
            
        if target:
            old_price = h.purchase_price
            
            if isinstance(target, tuple) and target[1]:
                # Total Cost provided
                total_cost = Decimal(target[0])
                new_unit_price = total_cost / h.quantity
            else:
                new_unit_price = Decimal(target)
                
            h.purchase_price = new_unit_price
            
            print(f"UPDATED {h.broker} | {h.ticker}: {old_price} -> {new_unit_price:.4f}")
            count += 1
            
    if count > 0:
        db.commit()
        print(f"--- Successfully patched {count} holdings ---")
    else:
        print("--- No matching holdings found to patch ---")

if __name__ == "__main__":
    patch_db()
