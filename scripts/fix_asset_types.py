import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding

def fix_asset_types():
    print("--- FIXING ASSET TYPES ---")
    session = SessionLocal()
    try:
        holdings = session.query(Holding).all()
        updated = 0
        
        crypto_suffixes = ['-USD', 'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'AVAX', 'TRX', 'TON', 'IOTA', 'HBAR', 'FET', 'POL', '1INCH', 'ENA', 'USDC', 'USDT', 'PNUT', 'MOVE', 'IO', 'BNSOL', 'MANA', 'SAND', 'VANA']
        crypto_names = ['BITCOIN', 'ETHEREUM', 'SOLANA', 'TETHER']
        
        for h in holdings:
            t = (h.ticker or "").upper()
            n = (h.name or "").upper()
            
            new_type = 'STOCK' # Default
            
            # 1. CASH
            if t in ['EUR', 'USD', 'GBP', 'CHF'] or 'CASH' in n:
                new_type = 'CASH'
                
            # 2. COMMODITY
            elif t in ['XAU', 'XAG']:
                new_type = 'COMMODITY'
                
            # 3. CRYPTO
            elif any(s in t for s in ['-USD']) or \
                 t in crypto_suffixes or \
                 any(c in n for c in crypto_names):
                 new_type = 'CRYPTO'
                 
            # 4. ETF
            elif 'ETF' in n or 'ISHARES' in n or 'VANGUARD' in n or 'XTRACKERS' in n or 'VANECK' in n:
                new_type = 'ETF'
            
            if h.asset_type != new_type:
                # print(f"{(h.ticker or 'N/A'):<15} : {h.asset_type} -> {new_type}")
                h.asset_type = new_type
                updated += 1
                
        print(f"Updating {updated} holdings...")
        session.commit()
        print("✅ DONE.")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fix_asset_types()
