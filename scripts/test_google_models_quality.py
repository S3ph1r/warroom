
import os
import subprocess
import json
import sys
from dotenv import load_dotenv

# Load env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    sys.exit(1)

# 1. Get List of Models
print("--- 1. Fetching Available Models ---")
url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
cmd_list = ["curl", "-s", url_list]

models_to_test = []

try:
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    if "models" in data:
        for m in data['models']:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                # Only take "pro" and "flash" models to avoid clutter (e.g. embedding models)
                name = m['name']
                if "gemini" in name and ("pro" in name or "flash" in name):
                     models_to_test.append(name)
    else:
        print("Error fetching models list.")
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print(f"Found {len(models_to_test)} candidate models (Pro/Flash).")

# 2. Test Each Model
prompt_text = "Spiega l'inflazione a un bambino di 5 anni in una frase."
payload = f'{{"contents":[{{"parts":[{{"text":"{prompt_text}"}}]}}]}}'

print(f"\n--- 2. Testing Quality (Prompt: '{prompt_text}') ---")

for model_name in models_to_test:
    # model_name format is usually "models/gemini-..."
    # API endpoint expects: v1beta/models/gemini... (passed as part of URL)
    # If the name already contains 'models/', we use it directly in the path if we construct strictly
    # Endpoint: https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent
    
    url_gen = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
    
    cmd_gen = [
        "curl", "-s",
        "-H", "Content-Type: application/json",
        "-d", payload,
        "-X", "POST",
        url_gen
    ]
    
    print(f"\nTesting: {model_name}...")
    try:
        res = subprocess.run(cmd_gen, capture_output=True, text=True, check=True)
        try:
            res_json = json.loads(res.stdout)
            if "candidates" in res_json and len(res_json["candidates"]) > 0:
                content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ RESPONSE: {content.strip()}")
            elif "error" in res_json:
                print(f"❌ ERROR: {res_json['error']['message']}")
            else:
                print(f"⚠️  NO CONTENT: {res_json}")
        except json.JSONDecodeError:
            print(f"❌ RAW OUTPUT ERROR: {res.stdout[:100]}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
