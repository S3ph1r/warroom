
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load env vars
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

print(f"Found GOOGLE_API_KEY (length: {len(api_key)})")

try:
    client = genai.Client(api_key=api_key)
    
    print("\n--- Testing gemini-1.5-pro ---")
    response = client.models.generate_content(
        model="gemini-1.5-pro",
        contents="Hello, are you Gemini 1.5 Pro?"
    )
    
    if response.text:
        print(f"Success! Response: {response.text[:100]}...")
    else:
        print("Response object returned but no text found.")
        print(response)

except Exception as e:
    print(f"Error: {e}")
