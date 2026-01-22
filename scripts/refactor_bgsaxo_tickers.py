from db.database import SessionLocal
from db.models import Holding, Transaction

def refactor_tickers():
    session = SessionLocal()
    try:
        print("Refactoring BGSAXO Tickers (Split Ticker:Market)...")
        print("=" * 60)
        
        # 1. Update Holdings
        holdings = session.query(Holding).filter(Holding.broker == "BGSAXO").all()
        h_count = 0
        for h in holdings:
            if h.ticker and ':' in h.ticker:
                parts = h.ticker.split(':')
                clean_ticker = parts[0].strip()
                market_code = parts[1].strip()
                
                print(f"🔧 Holding: {h.ticker} -> Tiker='{clean_ticker}', Market='{market_code}'")
                h.ticker = clean_ticker[:20] 
                h.market = market_code[:10]
                h_count += 1
                
        # 2. Update Transactions
        transactions = session.query(Transaction).filter(Transaction.broker == "BGSAXO").all()
        t_count = 0
        for t in transactions:
            if t.ticker and ':' in t.ticker:
                parts = t.ticker.split(':')
                clean_ticker = parts[0].strip()
                market_code = parts[1].strip()
                
                # Only log first few to avoid spam
                if t_count < 5:
                    print(f"🔧 Transaction: {t.ticker} -> Ticker='{clean_ticker}', Market='{market_code}'")
                
                t.ticker = clean_ticker[:20]
                t.market = market_code[:10]
                t_count += 1
        
        session.commit()
        print("-" * 60)
        print(f"✅ Completed! Updated {h_count} Holdings and {t_count} Transactions.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    refactor_tickers()
