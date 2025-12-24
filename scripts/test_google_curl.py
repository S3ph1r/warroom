
import os
import subprocess
import sys
from dotenv import load_dotenv

# Load env vars
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

print(f"Found GOOGLE_API_KEY (length: {len(api_key)})")

models_to_test = ["gemini-1.5-pro", "gemini-1.5-pro-latest", "gemini-1.5-pro-001", "gemini-1.5-pro-002"]

for model in models_to_test:
    print(f"\n--- Testing {model} ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data = '{"contents":[{"parts":[{"text":"Hello"}]}]}'
    
    command = [
        "curl", "-s",
        "-H", "Content-Type: application/json",
        "-d", data,
        "-X", "POST",
        url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if '"text":' in result.stdout:
            print(f"SUCCESS: {model} is working!")
            print(result.stdout[:200])
            break
        else:
            print(f"FAILED: {model}")
            print(result.stdout[:200]) # Print start of error
    except Exception as e:
        print(f"Error testing {model}: {e}")
