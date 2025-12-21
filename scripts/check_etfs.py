"""
Check how BG_SAXO ETFs are stored in DB
"""
import sys
sys.path.insert(0, '.')
from db.database import SessionLocal
from db.models import Holding

session = SessionLocal()

print("BG_SAXO ETFs in database:")
print("=" * 80)

etfs = session.query(Holding).filter(
    Holding.broker == 'BG_SAXO',
    Holding.asset_type == 'ETF'
).all()

for h in etfs:
    ticker = h.ticker
    isin = h.isin or "N/A"
    name = h.name[:40] if h.name else "?"
    
    # Check if ticker looks like an ISIN (12 chars, starts with letters)
    is_isin_format = len(ticker) == 12 and ticker[:2].isalpha()
    
    print(f"Ticker: {ticker:15} | ISIN: {isin:15} | ISIN-like: {is_isin_format} | {name}")

session.close()
