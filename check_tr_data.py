import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_tr_data():
    url = os.getenv("DATABASE_URL", "postgresql://warroom:warroom_dev_password@localhost:5432/warroom_db")
    print(f"Connecting to: {url}")
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            h_count = conn.execute(text("SELECT count(*) FROM holdings WHERE broker = 'TRADE_REPUBLIC'")).scalar()
            t_count = conn.execute(text("SELECT count(*) FROM transactions WHERE broker = 'TRADE_REPUBLIC'")).scalar()
            print(f"TR Holdings: {h_count}")
            print(f"TR Transactions: {t_count}")
            
            if h_count > 0:
                print("\nSample TR Holdings:")
                rows = conn.execute(text("SELECT * FROM holdings WHERE broker = 'TRADE_REPUBLIC' LIMIT 5")).mappings().all()
                for r in rows:
                    print(f"  - {r['ticker']}: {r['quantity']} (Value: {r['current_value']})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tr_data()
