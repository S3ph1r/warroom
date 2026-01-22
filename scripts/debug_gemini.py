
import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load Env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import google.generativeai as genai
from intelligence.llm_wrapper import GoogleProvider

# --- CONFIG ---
API_KEY = os.getenv("GOOGLE_API_KEY")
# Models in descending order of power/newness
CANDIDATE_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro-latest", 
    "gemini-1.5-flash", 
    "gemini-pro"
]

def test_direct_gemini():
    print(f"🔬 DEBUGGING GEMINI WATERFALL")
    
    if not API_KEY:
        print("❌ Missing API Key")
        return

    genai.configure(api_key=API_KEY)
    
    # SYSTEM PROMPT
    historian_prompt = "You are THE COUNCIL's Historian. Analyze financial context through historical parallels."
    
    # DATA SIZE CHECK
    payload_path = "debug_context_payload.json"
    if os.path.exists(payload_path):
        size = os.path.getsize(payload_path)
        print(f"📦 Context Payload Size: {size} bytes (~{size//4} tokens)")
    else:
        print("⚠️ Payload file not found, using dummy.")

    # QUERY
    risky_query = "Should I sell Bitcoin if it drops below 90k? Context: [Simulated 4KB Dossier]"

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for model_name in CANDIDATE_MODELS:
        print(f"\n--------------------------------")
        print(f"📉 TESTING: {model_name}")
        print(f"--------------------------------")
        
        try:
            model = genai.GenerativeModel(model_name, system_instruction=historian_prompt)
            print(f"   Sending query...")
            
            resp = model.generate_content(
                risky_query, 
                safety_settings=safety_settings
            )
            
            if resp.text:
                 print(f"   ✅ SUCCESS! Response length: {len(resp.text)}")
                 print(f"   Sample: {resp.text.strip()[:100]}...")
                 return
            else:
                 print(f"   ⚠️ Empty Response. Feedback: {resp.prompt_feedback}")
                 
        except Exception as e:
            print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    test_direct_gemini()
