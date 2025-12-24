
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

print(f"GOOGLE_API_KEY found (len={len(api_key)})")

# 1. List Models via CURL to find the exact name
print("\n--- Listing Models via CURL ---")
url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
cmd_list = ["curl", "-s", url_list]

found_pro = None
found_flash = None

try:
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
    try:
        data = json.loads(result.stdout)
        if "models" in data:
            print(f"Found {len(data['models'])} models.")
            for m in data['models']:
                name = m['name'] # e.g. models/gemini-1.5-pro
                display = m.get('displayName', '')
                if "gemini-1.5-pro" in name or "Gemini 1.5 Pro" in display:
                    print(f"MATCH PRO: {name} ({display})")
                    if not found_pro: found_pro = name
                if "gemini-1.5-flash" in name or "Gemini 1.5 Flash" in display:
                    print(f"MATCH FLASH: {name} ({display})")
                    if not found_flash: found_flash = name
        else:
            print("No 'models' key in response.")
            print(result.stdout[:200])
    except json.JSONDecodeError:
        print("Failed to decode JSON from curl:")
        print(result.stdout[:200])
except Exception as e:
    print(f"Curl error: {e}")

# 2. Test Generation with Found Model
target_model = found_pro if found_pro else found_flash
target_model = target_model or "models/gemini-1.5-pro" # Fallback

# Strip 'models/' prefix if present for some endpoints/SDKs, but keep for curl if needed
# The curl endpoint is usually .../models/{model}:generateContent
# If target_model is "models/gemini-1.5-pro", the URL should be .../models/gemini-1.5-pro:generateContent
# effectively using the full name in the URL path.
# But often the API expects JUST the model name in the ID part if the prefix is implied?
# Let's try constructing the URL carefully.
# If name is "models/gemini-1.5-pro", URL is https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent

model_id = target_model.replace("models/", "")
print(f"\n--- Testing Generation via CURL with model: {model_id} ---")

url_gen = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
payload = '{"contents":[{"parts":[{"text":"Describe the sea in 10 words."}]}]}'

cmd_gen = [
    "curl", "-s",
    "-H", "Content-Type: application/json",
    "-d", payload,
    "-X", "POST",
    url_gen
]

try:
    result = subprocess.run(cmd_gen, capture_output=True, text=True, check=True)
    print("Response snippet:")
    print(result.stdout[:300])
    if '"text":' in result.stdout:
        print("SUCCESS via CURL!")
    else:
        print("FAILURE via CURL.")
except Exception as e:
    print(f"Curl usage error: {e}")

# 3. Check Python Libs
print("\n--- Checking Python Libraries ---")
try:
    import google.generativeai as genai
    print("google.generativeai: INSTALLED")
except ImportError:
    print("google.generativeai: NOT INSTALLED")

try:
    import google.genai
    print("google.genai: INSTALLED")
except ImportError:
    print("google.genai: NOT INSTALLED")
