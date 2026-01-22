"""
Test Metadata Extraction
Verify that asset names are clean and metadata is populated correctly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Transaction

def test_metadata():
    session = SessionLocal()
    try:
        # Get Scalable Capital transactions
        txs = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL"
        ).order_by(Transaction.timestamp.desc()).limit(15).all()
        
        print("=" * 100)
        print("🔍 METADATA EXTRACTION TEST - Scalable Capital")
        print("=" * 100)
        print(f"{'TICKER (CLEAN)':<25} | {'CLASS':<8} | {'ADR':<6} | {'NOM':<8} | {'MKT':<5} | ISIN")
        print("-" * 100)
        
        for tx in txs:
            ticker = tx.ticker or "N/A"
            share_class = tx.share_class or "-"
            adr_ratio = str(tx.adr_ratio) if tx.adr_ratio else "-"
            nominal = tx.nominal_value or "-"
            market = tx.market or "-"
            isin = tx.isin or "N/A"
            
            print(f"{ticker:<25} | {share_class:<8} | {adr_ratio:<6} | {nominal:<8} | {market:<5} | {isin}")
        
        # Count metadata population
        total = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL"
        ).count()
        
        has_class = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL",
            Transaction.share_class.isnot(None)
        ).count()
        
        has_adr = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL",
            Transaction.adr_ratio.isnot(None)
        ).count()
        
        has_nominal = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL",
            Transaction.nominal_value.isnot(None)
        ).count()
        
        has_market = session.query(Transaction).filter(
            Transaction.broker == "SCALABLE_CAPITAL",
            Transaction.market.isnot(None)
        ).count()
        
        print("\n" + "=" * 100)
        print("📊 METADATA COVERAGE")
        print("=" * 100)
        print(f"Total Scalable Transactions: {total}")
        print(f"With share_class:   {has_class:>3} ({has_class/total*100:>5.1f}%)")
        print(f"With adr_ratio:     {has_adr:>3} ({has_adr/total*100:>5.1f}%)")
        print(f"With nominal_value: {has_nominal:>3} ({has_nominal/total*100:>5.1f}%)")
        print(f"With market:        {has_market:>3} ({has_market/total*100:>5.1f}%)")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_metadata()
