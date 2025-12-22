
from intelligence.engine import IntelligenceEngine
import logging

# Configure logging to show everything
logging.basicConfig(level=logging.INFO)

def debug_cycle():
    print("🚀 STARTING ENGINE DEBUG CYCLE")
    engine = IntelligenceEngine(portfolio_context="DEBUG CONTEXT")
    
    # Force run cycle
    print("👉 Running Cycle...")
    items = engine.run_cycle()
    
    print(f"\n🏁 Cycle Complete. Returned {len(items)} items.")
    for i in items[:5]:
        print(f"   [ITEM] {i['title']} ({i.get('source')})")

if __name__ == "__main__":
    debug_cycle()
