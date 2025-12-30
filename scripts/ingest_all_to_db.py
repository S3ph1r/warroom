
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, func
from sqlalchemy.orm import Session

# Setup Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import logic
try:
    from db.database import engine, SessionLocal
    from db.models import Transaction, Holding, IngestionBatch
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Configuration
FILES = {
    "BG SAXO": "scripts/bgsaxo_transactions_full.json",
    "SCALABLE CAPITAL": "scripts/scalable_transactions_full.json",
    "REVOLUT": "scripts/revolut_full_reconciled.json",
    "TRADE REPUBLIC": "scripts/tr_final.json",
    "BINANCE": "scripts/binance_final.json"
}

def clean_decimal(val):
    if val is None: return Decimal("0")
    try:
        return Decimal(str(val))
    except:
        return Decimal("0")

def ingest_file(session: Session, broker: str, filepath: str):
    path = PROJECT_ROOT / filepath
    if not path.exists():
        print(f"Skipping {broker}: File not found ({filepath})")
        return 0

    print(f"Ingesting {broker} from {filepath}...")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    txns = data.get("transactions", [])
    count = 0
    
    for t in txns:
        # Map fields
        # JSON: date, type, asset, isin, quantity, amount
        dt_str = t.get("date", "")
        # Parse date
        try:
            ts = datetime.strptime(dt_str[:10], "%Y-%m-%d")
        except:
            ts = datetime.utcnow() # Fallback

        qty = clean_decimal(t.get("quantity"))
        amt = clean_decimal(t.get("amount"))
        asset = t.get("asset", "Unknown").strip()
        isin = t.get("isin", "").strip()
        op = t.get("type", "UNKNOWN").upper()

        if not asset: asset = "Unknown"
        
        # Create Transaction
        db_txn = Transaction(
            broker=broker,
            ticker=asset[:20], # Limit length
            isin=isin[:12] if isin else None,
            operation=op,
            status="COMPLETED",
            quantity=qty,
            price=Decimal("0"), # Derived or 0
            total_amount=amt,
            timestamp=ts,
            source_document=Path(filepath).name,
            notes=f"Imported via Universal Ingest"
        )
        session.add(db_txn)
        count += 1
        
    session.commit()
    return count

def rebuild_holdings(session: Session):
    """
    Rebuild Holdings from Transactions.
    BUY operations ADD quantity, SELL operations SUBTRACT quantity.
    Only holdings with positive net quantity are created.
    """
    print("Rebuilding Holdings from Transactions...")
    
    # Clear Holdings
    session.execute(text("TRUNCATE TABLE holdings"))
    
    # Query with proper BUY/SELL sign handling
    # BUY, DEPOSIT, TRANSFER_IN, STAKING_REWARD, DIVIDEND -> positive
    # SELL, WITHDRAW, TRANSFER_OUT -> negative
    query = text("""
        SELECT 
            broker, 
            ticker, 
            SUM(
                CASE 
                    WHEN UPPER(operation) IN ('BUY', 'DEPOSIT', 'TRANSFER_IN', 'STAKING_REWARD', 
                                               'DIVIDEND', 'INTEREST', 'REWARD', 'AIRDROP', 
                                               'CASHBACK', 'EXCHANGE_IN') THEN quantity
                    WHEN UPPER(operation) IN ('SELL', 'WITHDRAW', 'TRANSFER_OUT', 'EXCHANGE_OUT',
                                               'FEE', 'TAX') THEN -quantity
                    ELSE quantity  -- Default: treat as positive (BUY-like)
                END
            ) as net_qty, 
            MAX(isin) as isin
        FROM transactions 
        GROUP BY broker, ticker 
        HAVING SUM(
            CASE 
                WHEN UPPER(operation) IN ('BUY', 'DEPOSIT', 'TRANSFER_IN', 'STAKING_REWARD', 
                                           'DIVIDEND', 'INTEREST', 'REWARD', 'AIRDROP', 
                                           'CASHBACK', 'EXCHANGE_IN') THEN quantity
                WHEN UPPER(operation) IN ('SELL', 'WITHDRAW', 'TRANSFER_OUT', 'EXCHANGE_OUT',
                                           'FEE', 'TAX') THEN -quantity
                ELSE quantity
            END
        ) > 0
    """)
    
    rows = session.execute(query).fetchall()
    
    count = 0
    for r in rows:
        broker = r[0]
        ticker = r[1]
        qty = Decimal(str(r[2]))
        isin = r[3]
        
        # Skip if quantity is zero or negative (fully sold)
        if qty <= 0:
            continue
        
        # Create Holding
        h = Holding(
            broker=broker,
            ticker=ticker,
            isin=isin,
            name=ticker,  # Will be enriched later
            asset_type="UNKNOWN",
            quantity=qty,
            current_value=Decimal("0"),
            currency="EUR"
        )
        session.add(h)
        count += 1
        
    session.commit()
    print(f"Created {count} Holdings (positive quantities only).")

def main():
    print("=== UNIVERSAL INGESTION START ===")
    session = SessionLocal()
    
    try:
        # 1. Truncate Tables
        print("Truncating old data...")
        session.execute(text("TRUNCATE TABLE transactions CASCADE"))
        session.execute(text("TRUNCATE TABLE holdings CASCADE"))
        session.commit()
        
        # 2. Ingest Files
        total_txns = 0
        for broker, path in FILES.items():
            cnt = ingest_file(session, broker, path)
            total_txns += cnt
            
        print(f"Total Transactions Inserted: {total_txns}")
        
        # 3. Rebuild Holdings
        rebuild_holdings(session)
        
        print("=== INGESTION COMPLETE ===")
        
    except Exception as e:
        print(f"Ingestion Failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
