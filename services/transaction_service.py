
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Transaction, Holding

class TransactionService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.own_db = db is None

    def close(self):
        if self.own_db:
            self.db.close()

    def _get_or_create_cash_holding(self, broker: str, currency: str) -> Holding:
        """Finds or creates a CASH holding for the broker."""
        cash = self.db.query(Holding).filter(
            Holding.broker == broker,
            Holding.asset_type == "CASH",
            Holding.currency == currency
        ).first()

        if not cash:
            # Create new CASH holding (Starting 0)
            cash = Holding(
                broker=broker,
                ticker=currency, # Ticker for cash is the currency code
                name=f"Cash ({currency})",
                asset_type="CASH",
                quantity=Decimal(0),
                current_value=Decimal(0),
                purchase_price=Decimal(1), # Cash cost basis is always 1 logic
                currency=currency,
                isin=None
            )
            self.db.add(cash)
            self.db.flush() # Get ID
        
        return cash

    def create_transaction(self, data: dict):
        """
        Executes a transaction:
        - Logs to Transaction table
        - Updates Holding (Quantity, Avg Cost)
        - Updates Cash Balance
        """
        try:
            # Parse Data
            mode = data.get("mode") # BUY, SELL, DEPOSIT, WITHDRAW
            broker = data.get("broker")
            ticker = data.get("ticker").upper()
            qty = Decimal(str(data.get("quantity")))
            price = Decimal(str(data.get("price") or 0)) # For Dep/With price is usually 1 or amount
            fees = Decimal(str(data.get("fees") or 0))
            currency = data.get("currency", "EUR")
            isin = data.get("isin") # NEW
            date_obj = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
            
            status = data.get("status", "COMPLETED")

            # 1. Create Transaction Record
            total_amount = qty * price
            
            tx = Transaction(
                broker=broker,
                ticker=ticker,
                operation=mode,
                status=status,
                quantity=qty,
                price=price,
                total_amount=total_amount,
                fees=fees,
                currency=currency,
                timestamp=datetime.now(), 
                # Note: Transaction model might not have ISIN column, but Holding does.
                # If Transaction has it, we should add it here too.
                # Assuming Transaction doesn't have it for now to avoid migration issues.
            )
            self.db.add(tx)
            
            # 2. Update Cash
            # Cash impact depends on mode
            cash_delta = Decimal(0)
            if mode == "BUY":
                cash_delta = -(total_amount + fees)
            elif mode == "SELL":
                cash_delta = total_amount - fees
            elif mode == "DEPOSIT":
                cash_delta = qty 
            elif mode == "WITHDRAW":
                cash_delta = -qty
            elif mode == "BALANCE":
                if data.get("asset_type") == "CASH":
                    cash_delta = qty
                else:
                    cash_delta = 0

            if mode in ["DEPOSIT", "WITHDRAW"] or (mode == "BALANCE" and data.get("asset_type") == "CASH"):
                cash_holding = self._get_or_create_cash_holding(broker, currency)
                cash_holding.quantity += cash_delta
                cash_holding.current_value = cash_holding.quantity 
            
            else:
                # TRADING (BUY/SELL)
                
                # Update Asset Holding
                holding = self.db.query(Holding).filter(
                    Holding.broker == broker,
                    Holding.ticker == ticker
                ).first()
                
                # Check Cash Availability (Optional, simplified for now)
                cash_holding = self._get_or_create_cash_holding(broker, currency)
                cash_holding.quantity += cash_delta
                cash_holding.current_value = cash_holding.quantity

                if mode == "BUY":
                    if not holding:
                        # New Holding
                        holding = Holding(
                            broker=broker,
                            ticker=ticker,
                            name=ticker, 
                            asset_type=data.get("asset_type", "STOCK"),
                            quantity=qty,
                            purchase_price=price, 
                            current_value=total_amount, 
                            currency=currency,
                            purchase_date=date_obj,
                            isin=isin # NEW
                        )
                        self.db.add(holding)
                    else:
                        # Existing: Update Weigthed Average
                        # Also update ISIN if missing
                        if not holding.isin and isin:
                            holding.isin = isin
                        # Existing: Update Weigthed Average Price
                        # New Avg = ((Old Qty * Old Avg) + (New Qty * New Price)) / (Old Qty + New Qty)
                        old_qty = holding.quantity
                        old_cost = holding.purchase_price or 0
                        
                        new_qty = old_qty + qty
                        if new_qty > 0: # Avoid division by zero
                            new_avg = ((old_qty * old_cost) + (qty * price)) / new_qty
                            holding.purchase_price = new_avg
                            holding.quantity = new_qty
                            # current_value will be updated by price fetcher, but we set it tentatively
                            holding.current_value = new_qty * (holding.current_price or price) 

                elif mode == "SELL":
                    if holding:
                        holding.quantity -= qty
                        # We don't change Avg Cost on Sell (FIFO/Weighted Avg logic usually keeps cost basis same per unit)
                        # Only total value changes
                         # current_value update
                        holding.current_value = holding.quantity * (holding.current_price or price)
                        
                        if holding.quantity <= 0:
                            # Close position? Or keep with 0?
                            # Usually keep with 0 to track history or delete. 
                            # Let's keep with 0 for now.
                            holding.quantity = 0
                            holding.current_value = 0

            self.db.commit()
            return {"status": "success", "tx_id": str(tx.id)}

        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            if self.own_db:
                self.close()

def log_transaction(data: dict):
    service = TransactionService()
    return service.create_transaction(data)
