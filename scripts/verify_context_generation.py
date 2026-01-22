
import sys
import json
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load Env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from services.portfolio_service import get_anonymous_portfolio_context
from intelligence.engine import IntelligenceEngine

def verify_context():
    print("🕵️  Verifying Council Context Generation (Local Only)...")
    
    # 1. Portfolio Context
    print("\n📊 Generating Anonymous Portfolio Context...")
    try:
        portfolio_ctx = get_anonymous_portfolio_context()
        print(f"   ✅ Success. Keys: {list(portfolio_ctx.keys())}")
        # Print a snippet
        print(f"   Sample Allocation: {portfolio_ctx.get('allocation')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        portfolio_ctx = {"error": str(e)}

    # 2. Market Briefing (Mistral)
    print("\n🗞️  Generating Daily Market Briefing (Mistral-Nemo)...")
    print("   (This may take 10-20 seconds on local CPU/GPU)")
    try:
        # Pass portfolio string context just in case engine needs it (though generate_daily_briefing uses memory)
        engine = IntelligenceEngine(portfolio_context=str(portfolio_ctx))
        
        briefing = engine.generate_daily_briefing()
        
        print(f"   ✅ Success. Briefing Length: {len(briefing)} chars")
        print("\n--- [MISTRAL BRIEFING START] ---")
        print(briefing)
        print("--- [MISTRAL BRIEFING END] ---\n")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        briefing = "Error generating briefing"

    # 3. Final Construct
    dossier = {
        "timestamp": "TEST_TIMESTAMP",
        "portfolio_summary": portfolio_ctx,
        "market_briefing": briefing,
        "user_specific_query": "Should I sell Bitcoin?" 
    }
    
    full_json = json.dumps(dossier, indent=2)
    print(f"\n📦 Final Payload Size: {len(full_json)} chars")
    
    # Save to file for inspection
    output_path = "debug_context_payload.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_json)
        
    print(f"💾 Full payload saved to: {output_path}")

if __name__ == "__main__":
    verify_context()
