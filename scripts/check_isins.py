import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding

def check_isins():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).all()
        print(f"Total Holdings: {len(holdings)}")
        
        with_isin = 0
        without_isin = 0
        sample_isins = []
        sample_no_isin = []
        
        for h in holdings:
            if h.isin and len(h.isin) >= 12:
                with_isin += 1
                if len(sample_isins) < 10:
                    sample_isins.append(f"{h.ticker}: {h.isin}")
            else:
                without_isin += 1
                if len(sample_no_isin) < 10:
                    sample_no_isin.append(h.ticker or h.name)
                    
        print(f"\nWith ISIN: {with_isin}")
        print(f"Without ISIN: {without_isin}")
        
        print("\n--- Sample ISINs ---")
        for s in sample_isins:
            print(f"  {s}")
            
        print("\n--- Sample WITHOUT ISIN ---")
        for s in sample_no_isin:
            print(f"  {s}")
            
    finally:
        session.close()

if __name__ == "__main__":
    check_isins()
