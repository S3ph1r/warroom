
import google.generativeai as genai
import os
import sys

# Load env vars manually/dotenv because user code assumed system env vars
from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("No GOOGLE_API_KEY")
    sys.exit(1)

# Configura l'API (legge automaticamente la variabile d'ambiente GOOGLE_API_KEY)
genai.configure(api_key=api_key)

print("Attempting with gemini-1.5-pro...")
try:
    # Seleziona il modello
    model = genai.GenerativeModel('gemini-1.5-pro')

    response = model.generate_content("Scrivi una breve poesia sul mare.")
    print("SUCCESS PRO:")
    print(response.text)
except Exception as e:
    print(f"FAILED PRO: {e}")

print("\nAttempting with gemini-1.5-flash...")
try:
    # Seleziona il modello
    model = genai.GenerativeModel('gemini-1.5-flash')

    response = model.generate_content("Scrivi una breve poesia sul mare.")
    print("SUCCESS FLASH:")
    print(response.text)
except Exception as e:
    print(f"FAILED FLASH: {e}")
