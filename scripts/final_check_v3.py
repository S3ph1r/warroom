
import google.generativeai as genai
import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Load env
from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

models_to_test = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp"
]

prompt = "Spiega l'inflazione a un bambino di 5 anni in una frase semplice e divertente."

output = []
output.append(f"--- COMPARAZIONE MODELLI GOOGLE ---")
output.append(f"Prompt: '{prompt}'\n")

for model_name in models_to_test:
    output.append(f">> Test Modello: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = response.text.replace("\n", " ").strip()
        output.append(f"   Risposta: {text}")
        output.append("-" * 60)
    except Exception as e:
        output.append(f"   Errore: {str(e)[:100]}...")
        output.append("-" * 60)

with open('results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Done. Wrote to results.txt")
