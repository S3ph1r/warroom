"""
BG SAXO COMPLETE WORKFLOW
1. Query DB for current holdings
2. Debug Pass 1 (structure analysis)
3. Pass 2 extraction with correct structure
4. Compare extracted vs DB
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from db.database import SessionLocal
from db.models import Holding

def query_bgsaxo_holdings():
    """Query DB for BG SAXO holdings."""
    print("="*70)
    print("STEP 1: CURRENT BG SAXO HOLDINGS IN DATABASE")
    print("="*70)
    
    session = SessionLocal()
    
    # Query holdings for BG_SAXO
    holdings = session.scalars(
        select(Holding).where(Holding.broker.ilike('%saxo%'))
    ).all()
    
    print(f"\nTotal BG SAXO holdings in DB: {len(holdings)}")
    print()
    
    total_value = Decimal('0')
    total_qty = Decimal('0')
    
    print(f"{'#':<3} {'Name':<35} {'Ticker':<10} {'ISIN':<15} {'Qty':<10} {'Price':<10} {'Value EUR':<12}")
    print("-"*105)
    
    for i, h in enumerate(holdings, 1):
        qty = h.quantity or Decimal('0')
        price = h.purchase_price or Decimal('0')
        value = qty * price
        total_qty += qty
        total_value += value
        
        print(f"{i:<3} {str(h.name or 'N/A')[:35]:<35} {str(h.ticker or '')[:10]:<10} {str(h.isin or '')[:15]:<15} {float(qty):<10.2f} {float(price):<10.2f} {float(value):<12.2f}")
    
    print("-"*105)
    print(f"{'TOTALE':<50} {'':<10} {'':<15} {float(total_qty):<10.2f} {'':<10} {float(total_value):<12.2f}")
    
    session.close()
    
    return holdings

if __name__ == "__main__":
    holdings = query_bgsaxo_holdings()
