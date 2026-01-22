from db.database import SessionLocal
from db.models import Holding

def fix_tickers():
    session = SessionLocal()
    try:
        # Map ISIN -> Correct Yahoo Ticker (EUR preferred for Scalable)
        corrections = {
            'KYG070341048': 'B1C.DE',    # Baidu (Xetra EUR) - Matches ~16 EUR
            'KYG875721634': 'NNNd.DE',   # Tencent (Xetra EUR) - Matches ~68 EUR
            'US2972842007': 'ESLOY',     # EssilorLuxottica ADR (US) - Matches ~134 EUR (converted)
                                         # EL.PA is ~220 EUR. The user has the ADR (ISIN US...).
            'CNE100006M58': '000333.SZ', # Midea Group (Shenzhen). 
        }
        
        print("Manual Ticker Fix for Scalable Pricing")
        print("=" * 40)
        
        for isin, new_ticker in corrections.items():
            holdings = session.query(Holding).filter(Holding.isin == isin).all()
            for h in holdings:
                old_t = h.ticker
                h.ticker = new_ticker
                print(f"✅ Updated {h.name[:30]} ({isin}): {old_t} -> {new_ticker}")
                
        session.commit()
        print("\nDatabase updated successfully.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fix_tickers()
