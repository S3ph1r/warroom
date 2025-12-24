
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load env vars
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

print(f"Found GOOGLE_API_KEY (length: {len(api_key)})")

genai.configure(api_key=api_key)

print("\n--- Listing Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- Testing gemini-1.5-pro ---")
try:
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content("Hello, can you confirm you are Gemini 1.5 Pro?")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Error generating content: {e}")
