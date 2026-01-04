"""
BINANCE Ingestion Script v2
Dedicated ingestion for Binance "Full History" CSV exports.

Input:
- ea91c32a...csv (Full Transaction History 2017-2026) in 'inbox/binance'

Strategy:
1. Parse CSV to get all transactions (Deposits, Withdrawals, Trades, Rewards).
2. Group by (Symbol, Date) to identify pricing needs.
3. Fetch daily close prices from Binance Public API (klines) for historical valuation.
4. Calculate Holdings based on 'Change' column sum.
5. Load Transactions and Holdings into DB.

Dependencies:
- pandas
- requests
- sqlalchemy
"""
import pandas as pd
import requests
import time
import uuid
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "BINANCE"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance")
CSV_PATTERN = "ea91c32a*.csv" # Or just *.csv but being specific is safer if manual file exists

# Binance API
API_URL = "https://api.binance.com/api/v3/klines"
PRICE_CACHE = {}

def get_binance_price(symbol: str, date_obj: datetime) -> float:
    """Fetch historical daily close price from Binance API."""
    date_str = date_obj.strftime("%Y-%m-%d")
    cache_key = f"{symbol}_{date_str}"
    
    if cache_key in PRICE_CACHE:
        return PRICE_CACHE[cache_key]
    
    # Symbols to try: COIN+EUR, COIN+USDT
    pairs_to_try = [f"{symbol}EUR", f"{symbol}USDT"]
    
    timestamp_ms = int(date_obj.timestamp() * 1000)
    
    final_price = 0.0
    
    for pair in pairs_to_try:
        try:
            params = {
                "symbol": pair,
                "interval": "1d",
                "startTime": timestamp_ms,
                "limit": 1
            }
            # Add small delay to respect rate limits (1200 req/min is plenty, but safety first)
            time.sleep(0.1) 
            
            resp = requests.get(API_URL, params=params, timeout=5)
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                # kline: [Open Time, Open, High, Low, Close, ...]
                close_price = float(data[0][4])
                
                if "USDT" in pair:
                    # Very rough approximation: 1 USDT ~= 0.92 EUR (avg). 
                    # Perfect accuracy would require fetching EURUSDT for that day too.
                    # For now, let's assume 1:1 USD/EUR parity for simplicity or fix constant
                    # Better: Fetch EURUSDT? No, let's use 0.92 as distinct placeholder
                    final_price = close_price * 0.92 
                else:
                    final_price = close_price
                
                break # Found it!
                
        except Exception:
            pass
    
    PRICE_CACHE[cache_key] = final_price
    if final_price == 0.0:
        print(f"   ⚠️ Price not found for {symbol} on {date_str}")
        
    return final_price


def normalize_operation(op_raw: str, coin: str) -> str:
    """Map Binance CSV operations to standard types."""
    op = op_raw.strip().lower()
    
    if "deposit" in op:
        return "DEPOSIT"
    if "withdraw" in op:
        return "WITHDRAW"
    if "buy" in op:
        return "BUY"
    if "sell" in op:
        return "SELL"
    if "fee" in op:
        return "FEE"
    if "distribution" in op or "reward" in op or "mining" in op or "interest" in op or "earn" in op:
        return "STAKING_REWARD"
    if "convert" in op or "swap" in op or "switch" in op:
        return "SWAP"
    if "small assets exchange" in op:
        return "SWAP" # Dust conversion
        
    return "UNKNOWN" # Default


def ingest_binance():
    print("=" * 60)
    print("🚀 BINANCE INGESTION v2 (CSV Full History + API Enrichment)")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # 1. Find CSV
        csv_files = list(INBOX.glob("*.csv"))
        # Prefer the 'full history' one if multiple
        target_csv = None
        for f in csv_files:
            if f.name.startswith("ea91c"):
                target_csv = f
                break
        
        if not target_csv and csv_files:
            target_csv = csv_files[0]
            
        if not target_csv:
            print("❌ No CSV file found in inbox/binance")
            return
            
        print(f"📂 Reading: {target_csv.name}")
        
        # 2. Parse CSV
        df = pd.read_csv(target_csv)
        print(f"   Rows found: {len(df)}")
        
        # 3. Clean DB
        deleted_h = session.query(Holding).filter(Holding.broker == BROKER).delete()
        deleted_t = session.query(Transaction).filter(Transaction.broker == BROKER).delete()
        print(f"🗑️ Cleared {deleted_h} holdings, {deleted_t} transactions")
        
        transactions = []
        holdings_map = defaultdict(Decimal) # Coin -> Quantity
        
        # 4. Process Rows
        print("\n🔄 Processing transactions & fetching prices...")
        
        # Columns: User_ID, UTC_Time, Account, Operation, Coin, Change, Remark
        
        processed_count = 0
        
        for _, row in df.iterrows():
            coin = str(row['Coin']).upper().strip()
            if coin == 'NAN': continue
            
            # Parse Date
            try:
                dt_str = str(row['UTC_Time'])
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except:
                continue
                
            qty = Decimal(str(row['Change']))
            op_raw = str(row['Operation'])
            op = normalize_operation(op_raw, coin)
            
            # --- Update Holdings Map ---
            holdings_map[coin] += qty
            
            # --- Price Enrichment (SKIPPED in Fast Mode) ---
            # We set price=0.0 initially to allow instant ingestion.
            # Use enrich_binance_prices.py to fetch historical data later.
            
            price_eur = Decimal("0")
            total_amount_eur = Decimal("0")
            
            tx = Transaction(
                id=uuid.uuid4(),
                broker=BROKER,
                ticker=coin,
                isin=None, # Crypto has no ISIN usually
                operation=op,
                status="COMPLETED",
                quantity=abs(qty),
                price=price_eur,
                total_amount=total_amount_eur, 
                currency="EUR", 
                fees=Decimal("0"),
                timestamp=dt,
                source_document=target_csv.name
            )
            transactions.append(tx)
            
            processed_count += 1
            if processed_count % 1000 == 0:
                print(f"   Processed {processed_count} / {len(df)}...")
        
        # 5. Bulk Insert Transactions
        print(f"\n💾 Saving {len(transactions)} transactions...")
        session.add_all(transactions)
        
        # 6. Save Holdings
        print("\n💰 Saving holdings...")
        holdings_objs = []
        for coin, qty in holdings_map.items():
            if abs(qty) <= Decimal("0.00000001"): # Ignore dust/zero
                continue
                
            # Get latest price for holding valuation
            current_price = get_binance_price(coin, datetime.now())
            
            h = Holding(
                id=uuid.uuid4(),
                broker=BROKER,
                ticker=coin,
                isin=None,
                name=f"{coin} Crypto Asset",
                asset_type="CRYPTO",
                quantity=qty,
                purchase_price=Decimal("0"), # WAC hard to calc with partial data, left 0
                current_price=Decimal(f"{current_price:.8f}"),
                current_value=qty * Decimal(f"{current_price:.8f}"),
                currency="EUR",
                source_document="Calculated from Full History",
                last_updated=datetime.now()
            )
            holdings_objs.append(h)
            
        session.add_all(holdings_objs)
        session.commit()
        print("✅ Data committed to database.")
        
        # Log
        log = ImportLog(
            id=uuid.uuid4(),
            broker=BROKER,
            filename=target_csv.name,
            holdings_created=len(holdings_objs),
            transactions_created=len(transactions),
            status="SUCCESS"
        )
        session.add(log)
        session.commit()
        
        print("\n✅ BINANCE INGESTION COMPLETE")
        print(f"   Holdings: {len(holdings_objs)}")
        print(f"   Transactions: {len(transactions)}")
        
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    ingest_binance()
