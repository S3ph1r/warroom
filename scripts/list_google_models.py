
import os
import subprocess
import json
import sys
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)
api_key = os.getenv("GOOGLE_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
cmd = ["curl", "-s", url]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    try:
        data = json.loads(result.stdout)
        if "models" in data:
            print(f"Found {len(data['models'])} models. Valid names:")
            for m in data['models']:
                # Filter for generateContent supported models
                if "generateContent" in m.get("supportedGenerationMethods", []):
                     print(f" - {m['name']}")
        else:
            print("No models found or error in response.")
            print(result.stdout[:200])
    except:
        print("JSON Error")
        print(result.stdout[:200])
except Exception as e:
    print(f"Error: {e}")
