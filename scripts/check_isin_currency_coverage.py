"""
Check ISIN and Currency Coverage
Verify that all holdings have ISIN and currency populated for all brokers.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

def check_coverage():
    session = SessionLocal()
    try:
        # Get all holdings grouped by broker
        all_holdings = session.query(Holding).all()
        
        brokers = {}
        for h in all_holdings:
            if h.broker not in brokers:
                brokers[h.broker] = {
                    'total': 0,
                    'missing_isin': [],
                    'missing_currency': [],
                    'complete': []
                }
            
            brokers[h.broker]['total'] += 1
            
            if not h.isin or h.isin.strip() == "":
                brokers[h.broker]['missing_isin'].append(h.ticker)
            
            if not h.currency or h.currency.strip() == "":
                brokers[h.broker]['missing_currency'].append(h.ticker)
            
            if h.isin and h.isin.strip() != "" and h.currency and h.currency.strip() != "":
                brokers[h.broker]['complete'].append(h.ticker)
        
        print("=" * 60)
        print("📊 ISIN & CURRENCY COVERAGE REPORT")
        print("=" * 60)
        
        for broker, data in sorted(brokers.items()):
            print(f"\n🏦 {broker}")
            print(f"   Total Holdings: {data['total']}")
            print(f"   ✅ Complete (ISIN + Currency): {len(data['complete'])}")
            print(f"   ❌ Missing ISIN: {len(data['missing_isin'])}")
            print(f"   ❌ Missing Currency: {len(data['missing_currency'])}")
            
            if data['missing_isin']:
                print(f"      Holdings without ISIN: {', '.join(data['missing_isin'][:5])}")
                if len(data['missing_isin']) > 5:
                    print(f"      ... and {len(data['missing_isin']) - 5} more")
            
            if data['missing_currency']:
                print(f"      Holdings without Currency: {', '.join(data['missing_currency'][:5])}")
                if len(data['missing_currency']) > 5:
                    print(f"      ... and {len(data['missing_currency']) - 5} more")
        
        # Overall summary
        total = sum(b['total'] for b in brokers.values())
        complete = sum(len(b['complete']) for b in brokers.values())
        missing_isin = sum(len(b['missing_isin']) for b in brokers.values())
        missing_currency = sum(len(b['missing_currency']) for b in brokers.values())
        
        print("\n" + "=" * 60)
        print("📈 OVERALL SUMMARY")
        print("=" * 60)
        print(f"Total Holdings: {total}")
        print(f"✅ Complete: {complete} ({complete/total*100:.1f}%)")
        print(f"❌ Missing ISIN: {missing_isin} ({missing_isin/total*100:.1f}%)")
        print(f"❌ Missing Currency: {missing_currency} ({missing_currency/total*100:.1f}%)")
        
        if complete == total:
            print("\n🎉 PERFECT! All holdings have ISIN and Currency!")
        else:
            print("\n⚠️ Some holdings are missing ISIN or Currency data.")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_coverage()
