
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from services.council import council

async def test_council():
    print("🔮 Summoning The Council (Connection Test)...")
    print(f"Google Key present: {bool(os.getenv('GOOGLE_API_KEY'))}")
    print(f"OpenRouter Key present: {bool(os.getenv('OPENROUTER_API_KEY'))}")
    
    context = """
    TEST CONTEXT:
    The user is verifying the AI connection.
    Portfolio: €10,000 in Bitcoin.
    Scenario: User asks if the connection works.
    """
    
    results = await council.convene_council(context)
    
    print("\n--- Council Verdicts ---")
    for role, advice in results.items():
        print(f"\n👤 role: {role.upper()}")
        if 'error' in advice:
            print(f"❌ Error: {advice['error']}")
        else:
            print(f"✅ Verdict: {advice.get('verdict')}")
            print(f"📝 Reasoning: {advice.get('reasoning')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_council())
