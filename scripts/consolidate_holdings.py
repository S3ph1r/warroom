"""
Consolidate Holdings Script
============================
This script merges duplicate holdings for the same ticker/broker,
combining positive and negative quantities into a single record.
"""
import sys
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding

def consolidate_holdings():
    print("--- CONSOLIDATING HOLDINGS ---")
    session = SessionLocal()
    
    try:
        holdings = session.query(Holding).all()
        print(f"Total Holdings Before: {len(holdings)}")
        
        # Group by (broker, ticker) - this is the logical unique key
        groups = defaultdict(list)
        for h in holdings:
            key = (h.broker, h.ticker)
            groups[key].append(h)
        
        print(f"Unique (broker, ticker) groups: {len(groups)}")
        
        # Find groups with multiple entries
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"Groups with duplicates: {len(duplicates)}")
        
        merged_count = 0
        deleted_count = 0
        
        for (broker, ticker), holdings_list in duplicates.items():
            # Calculate net quantity and weighted average price
            total_qty = Decimal('0')
            total_cost = Decimal('0')
            
            primary = holdings_list[0]  # Keep the first one
            
            for h in holdings_list:
                qty = h.quantity or Decimal('0')
                price = h.purchase_price or Decimal('0')
                
                total_qty += qty
                if qty > 0:
                    total_cost += qty * price
            
            # Calculate average purchase price (only from positive quantities)
            pos_qty = sum([h.quantity for h in holdings_list if h.quantity and h.quantity > 0], Decimal('0'))
            avg_price = total_cost / pos_qty if pos_qty > 0 else primary.purchase_price or Decimal('0')
            
            # Update primary record
            primary.quantity = total_qty
            primary.purchase_price = avg_price
            
            # If net quantity is zero or negative, we might want to delete
            # But for now, keep the record (user might have sold everything)
            
            # Delete the duplicates (keep only primary)
            for h in holdings_list[1:]:
                session.delete(h)
                deleted_count += 1
            
            merged_count += 1
            print(f"  Merged: {broker}/{ticker}: Net Qty = {total_qty}")
        
        # Also remove holdings with zero or negative final quantity
        remaining = session.query(Holding).all()
        zero_holdings = [h for h in remaining if h.quantity is None or h.quantity <= 0]
        
        print(f"\nHoldings with qty <= 0: {len(zero_holdings)}")
        for h in zero_holdings:
            print(f"  Removing: {h.ticker} (qty={h.quantity})")
            session.delete(h)
            deleted_count += 1
        
        session.commit()
        
        final_count = session.query(Holding).count()
        print(f"\n✅ DONE")
        print(f"   Merged Groups: {merged_count}")
        print(f"   Deleted Records: {deleted_count}")
        print(f"   Final Holdings: {final_count}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    consolidate_holdings()
