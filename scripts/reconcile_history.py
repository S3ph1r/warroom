
import sys
import os
from decimal import Decimal
from datetime import datetime
import uuid

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database import SessionLocal
from db.models import Transaction, Holding

def reconcile():
    db = SessionLocal()
    try:
        print("Starting Portfolio Reconciliation...")
        holdings = db.query(Holding).all()
        
        created_txs = 0
        
        for h in holdings:
            # 1. Sum up all existing transactions for this holding
            # 1. Sum up all existing transactions for this holding
            # Robust Matching: Match by Ticker OR ISIN
            # This handles cases where DB has ISIN as ticker (from PDF) vs Holdings Ticker
            txs = []
            
            # Primary Match: Ticker vs Ticker (Case Insensitive)
            txs_ticker = db.query(Transaction).filter(
                Transaction.broker == h.broker,
                Transaction.ticker.ilike(h.ticker)
            ).all()
            
            # Secondary Match: ISIN vs ISIN (if available)
            txs_isin = []
            if h.isin:
                txs_isin = db.query(Transaction).filter(
                    Transaction.broker == h.broker,
                    Transaction.isin == h.isin
                ).all()
                
            # Tertiary Match: Ticker field in DB holds the ISIN (common in current loader fallback)
            txs_ticker_is_isin = []
            if h.isin:
                 txs_ticker_is_isin = db.query(Transaction).filter(
                    Transaction.broker == h.broker,
                    Transaction.ticker == h.isin
                ).all()
            
            # Combine Unique Transactions
            seen_ids = set()
            txs = []
            for t in txs_ticker + txs_isin + txs_ticker_is_isin:
                if t.id not in seen_ids:
                    txs.append(t)
                    seen_ids.add(t.id)
            
            total_qty_tx = sum(t.quantity if t.operation in ['BUY', 'DEPOSIT', 'BALANCE'] else -t.quantity for t in txs)
            
            # 2. Calculate Delta
            # Note: Holding quantity is the "Truth" we want to match
            current_qty = h.quantity
            delta = current_qty - total_qty_tx
            
            # Tolerance for float/decimal math
            if abs(delta) < 0.000001:
                print(f"✅ {h.broker} | {h.ticker}: Matched ({current_qty})")
                continue
                
            print(f"⚠️  {h.broker} | {h.ticker}: Mismatch! Holding={current_qty}, History={total_qty_tx}, Delta={delta}")
            
            # 3. Create Synthetic Transaction
            if delta > 0:
                op = "BALANCE" # or BUY / DEPOSIT depending on asset type, but BALANCE is cleaner for history
                # Logic: We have MORE holdings than history says. We need to ADD history.
                qty = delta
            else:
                op = "BALANCE" # We have LESS holdings than history. We need to SUBTRACT history (negative qty? or SELL order?)
                # If we use BALANCE with negative qty, ensure system handles it. 
                # Better to use "SELL" or "WITHDRAW" semantics, or "BALANCE" with negative amount.
                # Let's use BALANCE with signed quantity if supported, otherwise explicit correction.
                # For BALANCE, let's assume it attempts to set a baseline. 
                # Actually, simplest is to just create a 'BALANCE' transaction of 'delta' amount.
                qty = delta
            
            # Get price from holding average cost
            price = h.purchase_price or h.current_price or 1
            if price is None: price = 1
            
            new_tx = Transaction(
                id=uuid.uuid4(),
                broker=h.broker,
                ticker=h.ticker,
                isin=h.isin,
                operation="BALANCE",
                quantity=abs(qty), # Operation direction defines sign usually? 
                # Wait, 'BALANCE' usually implies "Initial Balance". 
                # If we just add a transaction, we should follow standard flow:
                # BUY adds, SELL removes. 
                # If delta > 0 (we have more), we simulate a BUY/INFLOW.
                # If delta < 0 (we have less), we simulate a SELL/OUTFLOW.
                # Let's stick to BALANCE and let the system interpret it as Inflow/Outflow based on context or just handle it as a signed adjustment?
                # Standard practice: op='BALANCE', qty=signed_delta? 
                # Or op='BALANCE', qty=abs(delta), and we need a direction flag?
                # Let's map to existing ops for simplicity if 'BALANCE' isn't fully supported in FE logic yet.
                # But we defined BALANCE. Let's assume BALANCE acts like a BUY if positive? 
                # Actually, let's make it simple:
                # If delta > 0 -> "BALANCE" (treated as inflow)
                # If delta < 0 -> "CORRECTION" (treated as outflow)?
                # Let's just use BALANCE.
                price=price,
                total_amount=abs(qty) * price,
                currency=h.currency,
                timestamp=datetime(2024, 1, 1), # Default start of history or similar
                status="RECONCILED",
                source_document="RECONCILIATION_ENGINE",
                notes=f"Auto-generated reconciliation. Delta: {delta}"
            )
            
            # Hack for negative delta:
            # If we want to reduce history balance, we can't easily do it with just "BALANCE" unless we define it.
            # Let's assume BALANCE is valid. 
            # If delta < 0, we can mark it as a 'SELL' or 'WITHDRAW' conceptually?
            # Or just set quantity to negative in specific cases? 
            # Models usually expect positive quantity. 
            # Let's rely on operation type locally here.
            
            if delta < 0:
                # We need to reduce.
                # If we use 'BALANCE' with negative quantity, we need to ensure downstream analytics handle it.
                # Safer: usage 'BALANCE_OUT' or just 'SELL' with special note?
                # Let's Isolate:
                # If Asset is CASH -> WITHDRAW
                # If Asset is STOCK -> SELL
                op_type = "WITHDRAW" if h.asset_type == "CASH" else "SELL"
                new_tx.operation = op_type 
                new_tx.quantity = abs(delta)
                new_tx.notes = "Auto-generated reconciliation (Reduction)"
            else:
                 # We need to add.
                 # If Asset is CASH -> DEPOSIT
                 # If Asset is STOCK -> BUY (or BALANCE)
                 op_type = "DEPOSIT" if h.asset_type == "CASH" else "BALANCE"
                 new_tx.operation = op_type
                 new_tx.quantity = abs(delta)

            db.add(new_tx)
            created_txs += 1
            print(f"   -> Created {new_tx.operation} of {new_tx.quantity}")

        db.commit()
        print(f"\nReconciliation complete. Created {created_txs} transactions.")
        
        # Invalidate snapshot
        snapshot = os.path.join(project_root, "backend", "data", "portfolio_snapshot.json")
        if os.path.exists(snapshot):
            os.remove(snapshot)
            print("Snapshot invalidated.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reconcile()
