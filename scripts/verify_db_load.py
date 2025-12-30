"""
Verify DB Load
Check what was actually loaded into the DB.
"""
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

def get_db_url_inline():
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "warroom")
    return f"postgresql://{user}:{password}@{server}:{port}/{db}"

engine = create_engine(get_db_url_inline())

with engine.connect() as conn:
    print("📊 Transactions for ServiceNow (US81762P1021):")
    # Search by ISIN-like ticker
    rows = conn.execute(text("SELECT ticker, quantity, source_document FROM transactions WHERE ticker = 'US81762P1021'")).fetchall()
    
    if rows:
        for r in rows:
            print(f"✅ Found: Ticker={r[0]} Qty={r[1]} Source={r[2]}")
    else:
        print("❌ Not found by ISIN.")
        
    print("\n📊 Checking 'NOW:xnys' (Tickers):")
    rows = conn.execute(text("SELECT ticker FROM transactions WHERE ticker = 'NOW:xnys'")).fetchall()
    if rows:
        print("✅ Found by Ticker.")
    else:
        print("❌ Not found by Ticker.")
