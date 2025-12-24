
import os
import subprocess
import sys
from dotenv import load_dotenv

# Load env variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    sys.exit(1)

variations = [
    ("gemini-1.5-pro", "v1beta"), # Failed before, but keeping for comparison
    ("gemini-2.0-flash", "v1beta"), # Saw this in the list!
    ("gemini-flash-latest", "v1beta") # Saw this too
]

prompt_text = "Sei funzionante? Rispondi con 'Sì, sono operativo' e un breve saluto."
data = f'{{"contents":[{{"parts":[{{"text":"{prompt_text}"}}]}}]}}'

for model, version in variations:
    print(f"\n--- Testing {model} ({version}) ---")
    
    # Handle if model already has 'models/' prefix or not for URL construction.
    # The standard is /models/{model}:generateContent
    # If model has prefix "models/", we shouldn't add it again? No, usually model ID is just the name.
    
    if model.startswith("models/"):
        path_segments = model # already has 'models/'
    else:
        path_segments = f"models/{model}"

    url = f"https://generativelanguage.googleapis.com/{version}/{path_segments}:generateContent?key={api_key}"
    
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
            print("SUCCESS!")
            print(result.stdout[:500]) # Print first 500 chars
            break
        else:
            print(f"FAILED (Status: {result.stdout[:100]}...)")
    except Exception as e:
        print(f"Error: {e}")
