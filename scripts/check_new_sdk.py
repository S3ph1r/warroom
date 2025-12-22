
try:
    from google import genai
    print("✅ google-genai is installed.")
except ImportError:
    print("❌ google-genai is NOT installed.")
    print("Please run: pip install google-genai")
