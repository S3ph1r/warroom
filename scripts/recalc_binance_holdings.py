"""
Recalculate Binance Holdings WAC
Uses Enriched Transaction History to calculate Weighted Average Cost.
"""
import sys
from pathlib import Path
from decimal import Decimal
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recalc_wac():
    print("=" * 60)
    print("🧮 BINANCE WAC RECALCULATION")
    print("=" * 60)
    
    session = SessionLocal()
    try:
        # Get all Binance Holdings
        holdings = session.query(Holding).filter(Holding.broker == "BINANCE").all()
        
        print(f"🔄 Processing {len(holdings)} holdings...")
        
        updated = 0
        
        for h in holdings:
            # Get History
            txs = session.query(Transaction).filter(
                Transaction.broker == "BINANCE",
                Transaction.ticker == h.ticker
            ).order_by(Transaction.timestamp).all()
            
            if not txs: continue
            
            total_cost = Decimal(0)
            total_qty = Decimal(0)
            
            for tx in txs:
                price = tx.price if tx.price else Decimal(0)
                amount = tx.total_amount if tx.total_amount else (tx.quantity * price)
                
                if tx.operation in ["BUY", "DEPOSIT", "STAKING_REWARD", "DISTRIBUTION"]:
                    # Inflows increase cost basis
                    total_cost += amount
                    total_qty += tx.quantity
                    
                elif tx.operation in ["SELL", "WITHDRAW"]:
                    # Outflows reduce cost basis proportionally
                    if total_qty > 0:
                        avg_price = total_cost / total_qty
                        cost_reduction = avg_price * tx.quantity
                        total_cost -= cost_reduction
                        total_qty -= tx.quantity
                
                # Simple logic: prevent negative cost/qty drift
                if total_qty < 0: total_qty = Decimal(0)
                if total_cost < 0: total_cost = Decimal(0)

            # Calculate Final WAC
            wac = Decimal(0)
            if total_qty > 0:
                wac = total_cost / total_qty
            
            # Update Holding
            h.purchase_price = wac
            updated += 1
            # print(f"   {h.ticker}: WAC = {wac:.6f} EUR")
            
        session.commit()
        print(f"✅ Updated WAC for {updated} holdings.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    recalc_wac()
