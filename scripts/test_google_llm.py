
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os
from dotenv import load_dotenv
load_dotenv()

from intelligence.llm_wrapper import LLMWrapper

def test_google_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in .env")
        return
    
    print("Testing Google (Gemini) LLM Wrapper...")
    try:
        wrapper = LLMWrapper(provider="google", api_key=api_key, model="gemini-1.5-flash")
        print("✅ Google model initialized successfully!")
        
        # Quick test
        response = wrapper.chat([{"role": "user", "content": "Say 'Hello World' in Italian."}])
        print(f"Test Response: {response}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_model()
