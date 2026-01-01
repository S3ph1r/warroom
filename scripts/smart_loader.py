"""
Smart Database Loader & Holdings Calculator
Phase 4 of Ingestion Pipeline

Goal:
1. Load `extraction_results.json` into `transactions` table (Deduplicated).
2. IMMEDIATELY rebuild `holdings` table by replaying transaction history.

Source of Truth: `transactions` table.
Operational State: `holdings` table.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, and_

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.models import Transaction, Holding

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("warroom_ingestion.log", mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger("SmartLoader")

class SmartLoader:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.session = SessionLocal()
        self.new_transactions_count = 0
        self.skipped_count = 0

    def run(self):
        """Execute full atomic ingestion."""
        logger.info("="*60)
        logger.info("💾 SMART LOADER - Phase 4")
        logger.info("="*60)

        # 1. Load Transactions
        self._load_transactions()
        
        # 2. Rebuild Holdings (Atomic)
        self._rebuild_holdings()

        self.session.close()
        logger.info("="*60)
        logger.info("✅ DONE.")

    # ============================================================
    # STEP 1: LOAD TRANSACTIONS
    # ============================================================
    def _load_transactions(self):
        if not self.json_path.exists():
            logger.error(f"JSON file not found: {self.json_path}")
            return

        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"📂 Loading {len(data)} rows from {self.json_path.name}...")

        for row in data:
            try:
                self._upsert_transaction(row)
            except Exception as e:
                logger.error(f"❌ Error inserting row: {row} | Error: {e}")

        self.session.commit()
        logger.info(f"💾 Transactions Loaded: {self.new_transactions_count} new, {self.skipped_count} skipped.")

    def _upsert_transaction(self, row: dict):
        # 1. Parse fields
        broker = row.get("broker")
        date_str = row.get("date") # ISO format YYYY-MM-DD
        symbol = row.get("symbol", "UNKNOWN").strip()
        if not symbol: symbol = "UNKNOWN"
        
        operation = row.get("operation", "UNKNOWN").upper()
        
        # safely parse decimals
        qty = Decimal(str(row.get("quantity", 0)))
        price = Decimal(str(row.get("price", 0)))
        amount = Decimal(str(row.get("amount", 0)))
        fees = Decimal(str(row.get("fees", 0)))
        currency = row.get("currency", "EUR")
        source_doc = row.get("source_file")

        # Parse Timestamp
        # If date is just YYYY-MM-DD, add default time or use existing match
        try:
             ts = datetime.strptime(date_str, "%Y-%m-%d")
        except:
             ts = datetime.utcnow() # Fallback

        # 2. Deduplication Check
        # Strategy: Strict check on Broker + Ticker + Date + Amount + Operation
        exists = self.session.query(Transaction).filter(
            Transaction.broker == broker,
            Transaction.timestamp == ts,
            Transaction.ticker == symbol,
            Transaction.total_amount == amount,
            Transaction.operation == operation
        ).first()

        if exists:
            self.skipped_count += 1
            return

        # 3. Insert
        new_tx = Transaction(
            broker=broker,
            ticker=symbol,
            operation=operation,
            quantity=qty,
            price=price,
            total_amount=amount,
            fees=fees,
            currency=currency,
            timestamp=ts,
            source_document=source_doc,
            status="COMPLETED"
        )
        self.session.add(new_tx)
        self.new_transactions_count += 1


    # ============================================================
    # STEP 2: REBUILD HOLDINGS (CALCULATOR)
    # ============================================================
    def _rebuild_holdings(self):
        logger.info("\n🔄 REBUILDING HOLDINGS FROM HISTORY...")
        
        # 1. Identify impacted brokers
        # Ideally, we should rebuild only for brokers we just touched, 
        # but for safety/atomicity, let's rebuild REVOLUT (or all found in JSON).
        # Let's get unique brokers from the transactions table to be safe? 
        # Or just "REVOLUT" since that's what we are ingesting?
        # Let's be smart: Rebuild for all brokers found in the DB to ensure consistency.
        
        brokers = [b[0] for b in self.session.query(Transaction.broker).distinct().all()]
        logger.info(f"Target Brokers: {brokers}")

        for broker in brokers:
            self._recalc_broker_holdings(broker)
            
    def _recalc_broker_holdings(self, broker: str):
        logger.info(f"   🔨 Rebuilding {broker}...")
        
        # A. Fetch all history sorted by date
        txs = self.session.query(Transaction).filter(
            Transaction.broker == broker
        ).order_by(Transaction.timestamp.asc()).all()
        
        if not txs:
            return

        # B. In-Memory State: {ticker: {qty: Decimal, cost_basis: Decimal, ...}}
        portfolio = {} # Ticker -> State
        cash_balances = {} # Currency -> Decimal

        for tx in txs:
            ticker = tx.ticker
            op = tx.operation
            qty = tx.quantity
            amount = tx.total_amount # Usually total value (Price * Qty)
            currency = tx.currency
            
            # --- CASH HANDLING ---
            # If it's a pure CASH transaction (e.g. DEPOSIT, WITHDRAW) represented as a ticker="EUR" or empty
            # But usually we map these to specific Operations.
            
            # Update Cash Balance logic
            if currency not in cash_balances: cash_balances[currency] = Decimal(0)

            # Operations affecting Cash
            if op == "BUY":
                cash_balances[currency] -= amount # Outflow
            elif op == "SELL":
                cash_balances[currency] += amount # Inflow
            elif op == "DIVIDEND":
                cash_balances[currency] += amount
            elif op == "DEPOSIT":
                cash_balances[currency] += amount
            elif op == "WITHDRAW":
                cash_balances[currency] -= amount
            elif op == "FEE":
                 cash_balances[currency] -= amount
                 
            # --- POSITION HANDLING (STOCKS, CRYPTO, etc) ---
            if ticker and ticker != "UNKNOWN":
                if ticker not in portfolio:
                    portfolio[ticker] = {
                        "quantity": Decimal(0),
                        "total_cost": Decimal(0),
                        "wac": Decimal(0),
                        "asset_type": "STOCK", # Default, can infer from one of the TXs probably?
                        "name": ticker # Default name
                    }
                
                pos = portfolio[ticker]
                
                if op == "BUY":
                    # WAC Logic: (OldQty * OldWAC + NewQty * NewPrice) / (OldQty + NewQty)
                    # Simplified: Track Total Cost
                    pos["quantity"] += qty
                    pos["total_cost"] += amount
                    
                elif op == "SELL":
                    # FIFO or WAC? WAC usually reduces total cost proportionally
                    if pos["quantity"] > 0:
                         # Cost to remove = (SellQty / TotalQty) * TotalCost
                         # But logic: WAC stays same, Total Cost reduces
                         wac = pos["total_cost"] / pos["quantity"]
                         cost_removed = qty * wac # Approx
                         pos["total_cost"] -= cost_removed
                         pos["quantity"] -= qty
                    else:
                        # Selling from 0? Short?
                        pos["quantity"] -= qty
                        # Ignore cost for now
                        
                elif op == "TRANSFER_IN":
                    # Securities transferred in (e.g. from another broker)
                    # Adds quantity but with unknown cost basis (use amount if provided)
                    pos["quantity"] += qty if qty > 0 else amount
                    pos["total_cost"] += amount if amount > 0 else Decimal(0)

        # C. Commit to DB (Wipe & Replace)
        # 1. Delete existing holdings for this broker
        self.session.query(Holding).filter(Holding.broker == broker).delete()
        
        # 2. Insert Positions
        holdings_to_add = []
        
        # Positions
        for ticker, pos in portfolio.items():
            qty = pos["quantity"]
            # Filter dust (e.g. 0.00000001) or zero
            if abs(qty) < Decimal("0.000001"):
                continue
                
            # Name resolution could happen here or later
            avg_price = Decimal(0)
            if qty > 0:
                avg_price = pos["total_cost"] / qty
                
            h = Holding(
                broker=broker,
                ticker=ticker,
                name=pos["name"],
                asset_type="STOCK", # TODO: Infer better
                quantity=qty,
                purchase_price=avg_price,
                current_price=avg_price, # Temporary limit
                current_value=pos["total_cost"], # Temporary
                currency=currency # Assumption: last tx currency? A bit weak for multi-currency tickers
            )
            holdings_to_add.append(h)
            
        # Cash Positions
        for curr, bal in cash_balances.items():
             if abs(bal) > Decimal("0.01"):
                 h = Holding(
                     broker=broker,
                     ticker=curr, # e.g. "EUR"
                     name=f"Cash {curr}",
                     asset_type="CASH",
                     quantity=bal,
                     purchase_price=Decimal(1),
                     current_price=Decimal(1),
                     current_value=bal,
                     currency=curr
                 )
                 holdings_to_add.append(h)
                 
        self.session.add_all(holdings_to_add)
        self.session.commit()
        logger.info(f"   ✅ Recreated {len(holdings_to_add)} holdings for {broker}.")


if __name__ == "__main__":
    loader = SmartLoader(project_root / "extraction_results.json")
    loader.run()
