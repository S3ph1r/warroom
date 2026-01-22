"""
BINANCE Price Enrichment Script
Run this in background to fetch historical prices for transactions ingested with price=0.
"""
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import  and_

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction

# Configuration
BROKER = "BINANCE"
API_URL = "https://api.binance.com/api/v3/klines"
PRICE_CACHE = {}

def get_binance_price(symbol: str, date_obj: datetime) -> float:
    """Fetch historical daily close price from Binance API."""
    date_str = date_obj.strftime("%Y-%m-%d")
    cache_key = f"{symbol}_{date_str}"
    
    if cache_key in PRICE_CACHE:
        return PRICE_CACHE[cache_key]
    
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
            time.sleep(0.15) # 0.15s delay => ~400 req/min (Binance limit 1200)
            
            resp = requests.get(API_URL, params=params, timeout=5)
            data = resp.json()
            
            if isinstance(data, list) and len(data) > 0:
                close_price = float(data[0][4])
                if "USDT" in pair:
                    final_price = close_price * 0.92 
                else:
                    final_price = close_price
                break 
                
        except Exception:
            pass
    
    PRICE_CACHE[cache_key] = final_price
    return final_price


def run_enrichment():
    print("=" * 60)
    print("💰 BINANCE PRICE ENRICHMENT")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # PENDING_TXS: Transactions with 0 price (excluding FEEs/Deposits/Withdrawals if needed? No, user wanted P&L)
        # We target everything with status=0
        # Actually, Deposits/Withdrawals price isn't crucial for P&L but useful for Inflows.
        
        txs = session.query(Transaction).filter(
            Transaction.broker == BROKER,
            Transaction.price == 0,
            Transaction.operation.in_(['BUY', 'SELL', 'STAKING_REWARD', 'SWAP']) # Focus on trading ops first
        ).all()
        
        print(f"🔄 Found {len(txs)} transactions to enrich...")
        
        updated_count = 0
        not_found_count = 0
        
        for i, tx in enumerate(txs):
            # Skip valid 0 price (e.g. if quantity is 0? no)
            
            price = get_binance_price(tx.ticker, tx.timestamp)
            
            if price > 0:
                tx.price = Decimal(f"{price:.8f}")
                
                # Update total_amount based on quantity (assuming Change was the asset amount)
                amount = float(tx.quantity) * price
                tx.total_amount = Decimal(f"{amount:.8f}")
                
                updated_count += 1
            else:
                not_found_count += 1
                # print(f"   ⚠️ Price not found: {tx.ticker} on {tx.timestamp.date()}")
            
            if (i + 1) % 50 == 0:
                print(f"   Progress: {i + 1}/{len(txs)} | Updated: {updated_count} | Miss: {not_found_count}")
                session.commit() # Periodic commit
                
        session.commit()
        print("\n✅ ENRICHMENT COMPLETE")
        print(f"   Updated: {updated_count}")
        print(f"   Missing: {not_found_count}")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_enrichment()
