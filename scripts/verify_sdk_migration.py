
import sys
import os
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from intelligence.llm_wrapper import LLMWrapper

async def test_sdk():
    print("🚀 Testing New Google GenAI SDK Wrapper...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Missing API Key")
        return

    try:
        # Initialize Wrapper
        # Testing gemini-flash-latest (Final attempt)
        wrapper = LLMWrapper(provider="google", api_key=api_key, model="gemini-flash-latest")
        print("✅ Wrapper initialized with gemini-flash-latest.")
        
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'System Operational' if the SDK works."}
        ]
        
        # Call Chat (Async needed because we might want to check async compatibility later, 
        # but current wrapper implementation is synchronous calling async client? 
        # No, current impl uses synchronous client calls in a standard method.
        # Wait, the new SDK client is synchronous by default unless .aio is used.
        # So I can call it directly.)
        
        print("   Sending message...")
        response = wrapper.chat(msgs)
        
        if response:
            print(f"✅ Response: {response}")
        else:
            print("❌ Empty response or Error.")
            
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    # Test synchronous call first (as implemented in wrapper)
    asyncio.run(test_sdk())
