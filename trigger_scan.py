import sys
from pathlib import Path
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from intelligence.engine import IntelligenceEngine
from backend.main import build_intelligence_data

def run_scan():
    print("🚀 Starting Scan...")
    
    # Construct context (mocking what main.py does)
    context = "Portfolio: TEST_TICKER"
    
    engine = IntelligenceEngine(portfolio_context=context)
    new_items = engine.run_cycle()
    print(f"✅ Engine cycle complete. New items: {len(new_items)}")
    
    # Rebuild snapshot
    print("🔨 Building snapshot...")
    data = build_intelligence_data()
    print(f"✅ Snapshot built. Total items: {len(data)}")
    
    # Validation
    counts = {}
    for item in data:
        source = item.get('source', 'Unknown')
        counts[source] = counts.get(source, 0) + 1
        
    print("\nCounts per source:")
    max_exceeded = False
    for source, count in counts.items():
        print(f"- {source}: {count}")
        if count > 10:
            max_exceeded = True
            
    if max_exceeded:
        print("\n❌ FAILED: Limit of 10 items per source exceeded!")
    else:
        print("\n✅ PASSED: Limit respected.")

if __name__ == "__main__":
    run_scan()
