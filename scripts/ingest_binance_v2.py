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
print("DEBUG: Script started...")
import io

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
print("DEBUG: Imports 1 done")
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
print("DEBUG: Imports 2 done")

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog
print("DEBUG: DB Imports done")

# Configuration
BROKER = "BINANCE"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\binance")
CSV_PATTERN = "ea91c32a*.csv" # Or just *.csv but being specific is safer if manual file exists

# Binance API
API_URL = "https://api.binance.com/api/v3/klines"
PRICE_CACHE = {}
INVALID_PAIRS = set() # Cache for 400 Bad Request (Invalid Symbol)

# Optimize Connection: Global Session with Keep-Alive and Thread Pool
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
session.mount('https://', adapter)

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
        if pair in INVALID_PAIRS:
            continue
            
        try:
            params = {
                "symbol": pair,
                "interval": "1d",
                "startTime": timestamp_ms,
                "limit": 1
            }
            # Use global session for keep-alive
            resp = session.get(API_URL, params=params, timeout=5)
            
            if resp.status_code == 400:
                # Invalid symbol, cache it entirely for this pair
                INVALID_PAIRS.add(pair)
                continue
                
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                # kline: [Open Time, Open, High, Low, Close, ...]
                close_price = float(data[0][4])
                
                if "USDT" in pair:
                    final_price = close_price * 0.92 
                else:
                    final_price = close_price
                
                break # Found it!
                
        except Exception:
            pass
    
    PRICE_CACHE[cache_key] = final_price
    # if final_price == 0.0:
    #     print(f"   ⚠️ Price not found for {symbol} on {date_str}")
        
    return final_price


def normalize_operation(op_raw: str, coin: str) -> str:
    """Map Binance CSV operations to standard types."""
    op = op_raw.strip().lower()
    
    # Prioritize Transfers (Subscription/Redemption) to avoid capturing them as "Earn" rewards
    if "subscription" in op or "redemption" in op:
        return "TRANSFER"
        
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
    if "airdrop" in op:
        return "AIRDROP" 
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
        transactions = []
        holdings_map = {} # Coin -> {'qty': Decimal, 'total_cost': Decimal}
        
        # 4. Process Rows
        print("\n🔄 Scanning for unique (Coin, Date) pairs...")
        unique_pairs = set()
        for _, row in df.iterrows():
            coin = str(row['Coin']).upper().strip()
            if coin == 'NAN': continue
            try:
                dt_str = str(row['UTC_Time'])
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")
                
                op_raw = str(row['Operation'])
                op = normalize_operation(op_raw, coin)
                
                # Only fetch for relevant ops
                if op in ['BUY', 'SELL', 'SWAP', 'STAKING_REWARD', 'AIRDROP', 'DEPOSIT', 'WITHDRAW']:
                     unique_pairs.add((coin, date_str, dt))
            except:
                continue
                
        print(f"   Found {len(unique_pairs)} unique prices to fetch.")
        
        # --- PRE-FETCH PRICES IN PARALLEL ---
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_wrapper(args):
            coin, d_str, dt_obj = args
            # Check cache first
            if f"{coin}_{d_str}" in PRICE_CACHE:
                return
            get_binance_price(coin, dt_obj)
            
        print("   🚀 Pre-fetching prices (Parallel)...")
        with ThreadPoolExecutor(max_workers=50) as executor:
            # list of tasks
            tasks = [executor.submit(fetch_wrapper, p) for p in unique_pairs]
            
            done_count = 0
            for _ in as_completed(tasks):
                done_count += 1
                if done_count % 100 == 0:
                    sys.stdout.write(f"\r      Fetching: {done_count}/{len(unique_pairs)}")
                    sys.stdout.flush()
        print("\n   ✅ Pre-fetch complete.")

        print("\n🔄 Processing transactions...")
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
            
            # --- Price Enrichment ---
            # Fetch historical price immediately for WAC calculation
            price_eur = Decimal("0")
            if op in ['BUY', 'SELL', 'SWAP', 'STAKING_REWARD', 'AIRDROP', 'DEPOSIT', 'WITHDRAW']:
                 # Only fetch if meaningful for value (or if we want full history)
                 raw_price = get_binance_price(coin, dt)
                 price_eur = Decimal(f"{raw_price:.8f}")
            
            total_amount_eur = abs(qty) * price_eur
            
            # --- Update Holdings Map & WAC ---
            # Initialize if new
            if coin not in holdings_map:
                holdings_map[coin] = {'qty': Decimal('0'), 'total_cost': Decimal('0')}
            
            # WAC Logic:
            # If Inflow (Buy, Deposit, Airdrop, Reward, Swap In): Add to Cost Basis
            # If Outflow (Sell, Withdraw, Swap Out): Reduce Cost Basis proportionally
            
            if op == 'TRANSFER':
                # Ignore Internal Transfers (Subscription/Redemption) for Holdings calculation
                # to maintain a "Total Owned" view (Spot + Earn) from the Transaction History.
                pass
            elif qty > 0:
                # Inflow
                holdings_map[coin]['qty'] += qty
                holdings_map[coin]['total_cost'] += total_amount_eur
            elif qty < 0:
                # Outflow
                if holdings_map[coin]['qty'] > 0:
                     # Calculate current AVG price
                     avg_price = holdings_map[coin]['total_cost'] / holdings_map[coin]['qty']
                     # Reduce cost by qty * avg_price
                     cost_reduction = abs(qty) * avg_price
                     holdings_map[coin]['qty'] += qty # qty is negative, so it subtracts
                     holdings_map[coin]['total_cost'] -= cost_reduction
                else:
                     holdings_map[coin]['qty'] += qty
                     # Cost stays 0 or goes negative? Let's keep cost 0 if empty
            
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
            if processed_count % 50 == 0:
                print(f"   Processed {processed_count} / {len(df)}...")
        
        # 5. Bulk Insert Transactions
        print(f"\n💾 Saving {len(transactions)} transactions...")
        session.add_all(transactions)
        
        # 6. Save Holdings
        print("\n💰 Saving holdings...")
        holdings_objs = []
        for coin, data in holdings_map.items():
            qty = data['qty']
            total_cost = data['total_cost']
            
            if qty <= Decimal("0.00000001"): # Ignore dust/zero
                continue
                
            # Average Buy Price
            avg_buy_price = total_cost / qty if qty > 0 else Decimal("0")
                
            # Get latest price for holding valuation
            current_price = Decimal(f"{get_binance_price(coin, datetime.now()):.8f}")
            
            h = Holding(
                id=uuid.uuid4(),
                broker=BROKER,
                ticker=coin,
                isin=None,
                name=f"{coin} Crypto Asset",
                asset_type="CRYPTO",
                quantity=qty,
                purchase_price=avg_buy_price,
                current_price=current_price,
                current_value=qty * current_price,
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
        
        # Invalidate cache
        cache_path = Path(__file__).parent.parent / "data" / "portfolio_snapshot.json"
        if cache_path.exists():
            cache_path.unlink()
            print("🔄 Portfolio cache invalidated (Dashboard will refresh)")
        
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    ingest_binance()
