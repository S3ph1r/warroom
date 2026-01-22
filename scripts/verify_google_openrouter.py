
import asyncio
import os
import sys

from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env vars from project root .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)
print(f"Loaded environment from: {env_path}")
print(f"OPENROUTER_API_KEY type: {type(os.getenv('OPENROUTER_API_KEY'))}")

from intelligence.llm_wrapper import LLMWrapper

async def test_google_via_openrouter():
    print("Initializing LLMWrapper for Google (OpenRouter)...")
    try:
        # Based on services/council.py, the model name is "google/gemini-2.0-flash-exp:free"
        # and provider is "openrouter" effectively, but the key is 'google' in the initialization map.
        # Wait, in council.py we established:
        # "google": LLMWrapper(provider="openrouter", model="google/gemini-2.0-flash-exp:free", ...)
        
        llm = LLMWrapper(
            provider="openrouter",
            model="google/gemini-2.0-flash-exp:free",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        print("Sending test query...")
        # LLMWrapper.chat is synchronous
        response = llm.chat("Hello, are you functioning correctly?")
        
        if response:
            print(f"Success! Response: {response[:100]}...")
        else:
            print("Failed: Response was None or empty.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_google_via_openrouter())
