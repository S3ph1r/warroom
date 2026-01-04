"""
BGSAXO Reconciliation Script
Verifies that holdings match transaction history.
"""
import sys
from pathlib import Path
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction

BROKER = "BGSAXO"


def run_reconciliation():
    print("=" * 60)
    print("🔍 BGSAXO RECONCILIATION")
    print("=" * 60)
    
    session = SessionLocal()
    
    # Get all BGSAXO holdings
    holdings = session.query(Holding).filter(Holding.broker == BROKER).all()
    print(f"\n📦 Holdings from snapshot: {len(holdings)}")
    
    # Get all BGSAXO transactions and calculate net position per ticker/ISIN
    transactions = session.query(Transaction).filter(Transaction.broker == BROKER).all()
    print(f"📜 Transactions in history: {len(transactions)}")
    
    # Calculate positions from transactions
    positions_from_tx = defaultdict(lambda: {"qty": Decimal("0"), "buys": 0, "sells": 0, "isin": None})
    
    for tx in transactions:
        key = tx.isin if tx.isin else tx.ticker
        
        if tx.operation == "BUY":
            positions_from_tx[key]["qty"] += tx.quantity
            positions_from_tx[key]["buys"] += 1
        elif tx.operation == "SELL":
            positions_from_tx[key]["qty"] -= tx.quantity
            positions_from_tx[key]["sells"] += 1
            
        if tx.isin:
            positions_from_tx[key]["isin"] = tx.isin
    
    print(f"\n🧮 Calculated positions from transactions: {len(positions_from_tx)}")
    
    # Reconcile
    print("\n" + "=" * 60)
    print("RECONCILIATION RESULTS")
    print("=" * 60)
    
    matched = 0
    mismatched = 0
    not_found = 0
    
    for h in holdings:
        key = h.isin if h.isin else h.ticker
        
        if key in positions_from_tx:
            calc_qty = positions_from_tx[key]["qty"]
            snapshot_qty = h.quantity
            
            # Check if quantities match (within tolerance for decimals)
            diff = abs(calc_qty - snapshot_qty)
            if diff < Decimal("0.01"):
                matched += 1
                status = "✅"
            else:
                mismatched += 1
                status = "❌"
                print(f"\n{status} {h.name[:30]}")
                print(f"   ISIN: {h.isin}")
                print(f"   Snapshot qty: {snapshot_qty}")
                print(f"   Calculated qty: {calc_qty}")
                print(f"   Diff: {diff}")
                print(f"   Buys: {positions_from_tx[key]['buys']}, Sells: {positions_from_tx[key]['sells']}")
        else:
            not_found += 1
            print(f"\n⚠️ {h.name[:30]} - No transactions found!")
            print(f"   ISIN: {h.isin}, Ticker: {h.ticker}")
            print(f"   Snapshot qty: {h.quantity}")
    
    # Check for orphan transactions (positions sold to zero)
    zero_positions = [(k, v) for k, v in positions_from_tx.items() if v["qty"] == 0]
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Matched: {matched}")
    print(f"❌ Mismatched: {mismatched}")
    print(f"⚠️ Holdings without transactions: {not_found}")
    print(f"📉 Positions sold to zero: {len(zero_positions)}")
    
    if mismatched == 0 and not_found == 0:
        print("\n🎉 PERFECT RECONCILIATION!")
    else:
        print(f"\n⚠️ Reconciliation issues found")
    
    session.close()


if __name__ == "__main__":
    run_reconciliation()
