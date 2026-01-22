"""
Check Asset Names and Tickers
Analyze ticker and name fields to identify any issues with extraction.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding

def check_names():
    session = SessionLocal()
    try:
        holdings = session.query(Holding).all()
        
        print("=" * 80)
        print("📋 ASSET NAMES & TICKERS ANALYSIS")
        print("=" * 80)
        
        # Group by broker
        by_broker = {}
        for h in holdings:
            if h.broker not in by_broker:
                by_broker[h.broker] = []
            by_broker[h.broker].append(h)
        
        for broker in sorted(by_broker.keys()):
            print(f"\n🏦 {broker}")
            print("-" * 80)
            print(f"{'TICKER':<25} | {'NAME':<50}")
            print("-" * 80)
            
            for h in sorted(by_broker[broker], key=lambda x: x.ticker):
                ticker = h.ticker or "N/A"
                name = h.name or "N/A"
                
                # Highlight potential issues
                issues = []
                if len(ticker) > 20:
                    issues.append("LONG_TICKER")
                if any(char in ticker for char in ['.', '/', '(', ')', '-', ' ']):
                    issues.append("SPECIAL_CHARS")
                if len(name) > 30:
                    issues.append("LONG_NAME")
                
                marker = " ⚠️" if issues else ""
                print(f"{ticker:<25} | {name:<50} {marker}")
                if issues:
                    print(f"{'':>25}   Issues: {', '.join(issues)}")
        
        # Sample problematic entries
        print("\n" + "=" * 80)
        print("🔍 DETAILED ANALYSIS OF POTENTIAL ISSUES")
        print("=" * 80)
        
        print("\n📌 Entries with special characters in ticker:")
        for h in holdings:
            if any(char in (h.ticker or "") for char in ['.', '/', '(', ')', ' ']):
                print(f"  Broker: {h.broker}")
                print(f"  Ticker: '{h.ticker}'")
                print(f"  Name: '{h.name}'")
                print(f"  ISIN: {h.isin or 'N/A'}")
                print()
        
        print("\n📌 Entries with very long names (>30 chars):")
        for h in holdings:
            if len(h.name or "") > 30:
                print(f"  Broker: {h.broker}")
                print(f"  Ticker: '{h.ticker}'")
                print(f"  Name: '{h.name}' (len={len(h.name)})")
                print(f"  ISIN: {h.isin or 'N/A'}")
                print()
                
    finally:
        session.close()

if __name__ == "__main__":
    check_names()
