"""
IBKR Ingestion Script v2
Strategy: CSV ONLY (Full History since account opened in 2025).
Enrichment: Manual ISINs + WAC Calculation.
"""
import uuid
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "IBKR"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\ibkr")

# Manual ISIN Enrichment
ISIN_MAP = {
    "RGTI": "US76655K1034",
    "3CP": "KYG9830T1067", # Xiaomi Corp
    "UAMY": "US9115491030" 
}

def parse_ibkr_csv(csv_path: Path):
    """
    Parses IBKR Transaction History CSV.
    """
    transactions = []
    print(f"📊 Parsing CSV: {csv_path.name}")
    
    try:
        lines = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        header_line_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("Transaction History,Header,"):
                header_line_idx = i
                break
                
        if header_line_idx == -1:
            print("❌ 'Transaction History' section not found in CSV.")
            return []
            
        headers = lines[header_line_idx].strip().split(',')
        
        try:
            date_idx = headers.index('Date')
            desc_idx = headers.index('Description')
            type_idx = headers.index('Transaction Type')
            sym_idx = headers.index('Symbol')
            qty_idx = headers.index('Quantity')
            price_idx = headers.index('Price')
            amt_idx = headers.index('Net Amount')
            comm_idx = headers.index('Commission')
            isin_idx = next((i for i, h in enumerate(headers) if 'ISIN' in h), -1)
        except ValueError as e:
            print(f"❌ Missing column in CSV header: {e}")
            return []
            
        for line in lines[header_line_idx+1:]:
            if not line.startswith("Transaction History,Data,"):
                continue
                
            parts = line.strip().split(',')
            
            try:
                symbol = parts[sym_idx]
                if not symbol or symbol == "": continue
                
                tx_type = parts[type_idx].lower()
                op = "UNKNOWN"
                
                # Operation Mapping
                if "buy" in tx_type or "acquisto" in tx_type: op = "BUY"
                elif "sell" in tx_type or "vendita" in tx_type: op = "SELL"
                elif "dividend" in tx_type or "dividendo" in tx_type: op = "DIVIDEND"
                elif "deposit" in tx_type or "deposito" in tx_type: op = "DEPOSIT"
                elif "withdraw" in tx_type or "prelievo" in tx_type: op = "WITHDRAW"
                elif "fee" in tx_type or "commissione" in tx_type: op = "FEE"
                elif "interest" in tx_type or "interesse" in tx_type: op = "INTEREST"
                
                qty = Decimal(parts[qty_idx]) if parts[qty_idx] else Decimal(0)
                price = Decimal(parts[price_idx]) if parts[price_idx] else Decimal(0)
                total_amt = Decimal(parts[amt_idx]) if parts[amt_idx] else Decimal(0)
                fees = Decimal(parts[comm_idx]) if comm_idx >= 0 and parts[comm_idx] else Decimal(0)
                isin = parts[isin_idx] if isin_idx >= 0 else None
                dt = datetime.strptime(parts[date_idx], "%Y-%m-%d")

                # Enrich ISIN if missing
                if not isin and symbol in ISIN_MAP:
                    isin = ISIN_MAP[symbol]

                transactions.append(Transaction(
                    id=uuid.uuid4(),
                    broker=BROKER,
                    ticker=symbol,
                    isin=isin,
                    operation=op,
                    status="COMPLETED",
                    quantity=abs(qty),
                    price=abs(price),
                    total_amount=abs(total_amt),
                    currency="EUR",
                    fees=abs(fees),
                    timestamp=dt,
                    source_document=csv_path.name
                ))
                
            except Exception:
                continue
                
        print(f"   Parsed {len(transactions)} transactions.")
        return transactions
        
    except Exception as e:
        print(f"❌ Critical CSV Error: {e}")
        return []

def ingest_ibkr():
    print("=" * 60)
    print("🚀 IBKR INGESTION (CSV Only + WAC Calculation)")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        csv_files = list(INBOX.glob("*.csv"))
        if not csv_files:
            print("❌ No CSV found in inbox/ibkr")
            return
        
        # Take the largest CSV or specific naming convention? Just the first one for now.
        csv_file = csv_files[0]
        
        # Clear DB
        session.query(Holding).filter(Holding.broker == BROKER).delete()
        session.query(Transaction).filter(Transaction.broker == BROKER).delete()
        print("🗑️ Cleared previous data.")
        
        # 1. Parse Transactions
        transactions = parse_ibkr_csv(csv_file)
        
        # 2. Calculate Holdings & Cost Basis
        holdings_map = {} # Ticker -> Quantity
        cost_map = {}     # Ticker -> Total Cost (EUR)
        
        # User confirmed single 500 EUR deposit missing from 1Y History
        cash_balance = Decimal(500) 
        
        print(f"\n🧮 Calculating Holdings & Cash (Starting with {cash_balance} EUR)...")
        
        for tx in transactions:
            if tx.ticker not in holdings_map:
                holdings_map[tx.ticker] = Decimal(0)
                cost_map[tx.ticker] = Decimal(0)
            
            # Stock Movement
            if tx.operation == "BUY":
                holdings_map[tx.ticker] += tx.quantity
                cost_map[tx.ticker] += tx.total_amount # Add absolute cost (total_amount usually negative in csv? we parsed as ABS)
                # Check ABS logic: parse_ibkr_csv takes abs(). Good.
                
                # Cash Flow: Spend total_amount (which is usually cost)
                cash_balance -= tx.total_amount 
                
            elif tx.operation == "SELL":
                # Basic Average Cost Reduction
                old_qty = holdings_map[tx.ticker]
                holdings_map[tx.ticker] -= tx.quantity
                
                if old_qty > 0:
                     avg_price = cost_map[tx.ticker] / old_qty
                     cost_reduction = avg_price * tx.quantity
                     cost_map[tx.ticker] -= cost_reduction
                
                # Sell means cash IN.
                cash_balance += tx.total_amount
                
            elif tx.operation == "DEPOSIT": 
                if tx.quantity > 0: # Stock Transfer In
                     holdings_map[tx.ticker] += tx.quantity
                else:
                    if tx.ticker == "EUR":
                         cash_balance += tx.total_amount
            
            elif tx.operation == "WITHDRAW":
                if tx.quantity > 0:
                     holdings_map[tx.ticker] -= tx.quantity
                else: 
                     if tx.ticker == "EUR":
                         cash_balance -= tx.total_amount
            
            elif tx.operation == "DIVIDEND":
                 cash_balance += tx.total_amount
                 
            # Handle Fees (Subtracted from cash)
            if tx.fees and tx.fees > 0:
                cash_balance -= tx.fees

        holdings_objs = []
        
        # Add Cash Holding
        print(f"   💰 Cash Balance Calculated: {cash_balance} EUR")
        
        holdings_objs.append(Holding(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker="EUR",
            name="Euro",
            asset_type="CURRENCY",
            quantity=cash_balance,
            current_value=cash_balance,
            currency="EUR",
            source_document="Calculated from CSV",
            last_updated=datetime.now()
        ))

        for ticker, qty in holdings_map.items():
            if abs(qty) < Decimal("0.0001"): continue
            
            # Resolve ISIN
            isin = ISIN_MAP.get(ticker)
            
            # Calculate Avg Price
            avg_price = Decimal(0)
            if qty > 0 and cost_map[ticker] > 0:
                avg_price = cost_map[ticker] / qty

            holdings_objs.append(Holding(
                id=uuid.uuid4(),
                broker=BROKER,
                ticker=ticker,
                name=ticker, 
                asset_type="STOCK", 
                quantity=qty,
                isin=isin,                   # POPULATED
                purchase_price=avg_price,    # POPULATED
                current_value=Decimal(0),    # Needs live price
                currency="EUR", 
                source_document="Calculated from CSV",
                last_updated=datetime.now()
            ))
            
        print(f"   Calculated {len(holdings_objs)} holdings.")
        
        # Save
        try:
            session.add_all(transactions)
            session.add_all(holdings_objs)
            session.commit()
            
            # Log
            session.add(ImportLog(
                id=uuid.uuid4(),
                broker=BROKER,
                filename=csv_file.name,
                holdings_created=len(holdings_objs),
                transactions_created=len(transactions),
                status="SUCCESS"
            ))
            session.commit()
            
            print("\n✅ IBKR INGESTION COMPLETE")
            print(f"   Holdings: {len(holdings_objs)}")
            print(f"   Transactions: {len(transactions)}")
            
        except Exception as db_err:
            session.rollback()
            print(f"❌ DB Error: {db_err}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    ingest_ibkr()
