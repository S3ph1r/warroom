import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.council import TheCouncil

async def test_council():
    print("=== Testing The Council (Google Model) ===\n")
    load_dotenv()
    
    council = TheCouncil()
    
    # Check if models are initialized
    print("Models initialized:")
    for model_name, model in council.models.items():
        status = "✅" if model else "❌"
        print(f"{status} {model_name}: {type(model)}")
    
    print("\n=== Testing Google Model Specifically ===")
    if 'google' not in council.models:
        print("❌ Google model not found in council.models")
        return
    
    # Test a simple consultation
    print("\nTesting a simple consultation with Google Historian...")
    try:
        result = await council.consult_model_persona(
            'google', 
            'historian', 
            "Test context: What is the current market sentiment?"
        )
        print(f"\n✅ Google Response: {result}")
    except Exception as e:
        print(f"\n❌ Error calling Google model: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Checking API Keys ===")
    google_key = os.getenv("GOOGLE_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    print(f"GOOGLE_API_KEY: {'✅ Set' if google_key else '❌ Missing'}")
    print(f"OPENROUTER_API_KEY: {'✅ Set' if openrouter_key else '❌ Missing'}")
    
    if openrouter_key:
        print(f"OpenRouter Key (masked): {openrouter_key[:8]}...{openrouter_key[-4:]}")

if __name__ == "__main__":
    asyncio.run(test_council())
