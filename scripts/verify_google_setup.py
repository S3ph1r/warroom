import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.llm_wrapper import LLMWrapper

def check_setup():
    print("--- Checking Google Setup ---")
    load_dotenv()
    
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("❌ GOOGLE_API_KEY is MISSING in .env or environment.")
    else:
        masked = key[:4] + "..." + key[-4:]
        print(f"✅ GOOGLE_API_KEY found: {masked}")
        
    print("\n--- Listing Available Models (google.genai) ---")
    try:
        from google import genai
        client = genai.Client(api_key=key)
        # Iterate over the Pager object
        for m in client.models.list():
             # We only care about generateContent models
             if "generateContent" in (m.supported_actions or []):
                print(f"- {m.name}")
    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        
    print("\n--- Testing LLMWrapper Init (gemini-flash-latest) ---")
    try:
        google_model = LLMWrapper(
            provider="google", 
            api_key=key,
            model="gemini-2.0-flash" 
        )
        print("✅ LLMWrapper initialized successfully.")
        
        print("\n--- Testing Simple Chat ---")
        try:
            response = google_model.chat([{"role": "user", "content": "Hello"}])
            print(f"✅ Response received: {response}")
        except Exception as chat_err:
            print(f"❌ Chat failed: {chat_err}")
            
    except Exception as e:
        print(f"❌ LLMWrapper Init Failed: {e}")

if __name__ == "__main__":
    check_setup()
