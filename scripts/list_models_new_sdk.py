
import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

print("Fetching available models (New SDK)...")
try:
    for m in client.models.list():
        print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
