import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def test_google_direct():
    api_key = os.getenv("GOOGLE_API_KEY")
    # Using the model discovered in user screenshot/list
    model_name = "gemini-2.5-flash"
    
    print(f"--- Simulating Google Direct Call ({model_name}) ---")
    print(f"Using API Key: {api_key[:8]}...{api_key[-4:] if api_key else 'None'}")
    
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env")
        return

    try:
        client = genai.Client(api_key=api_key)
        
        # Simple test prompt
        prompt = "Sei lo Storico del Consiglio. Analizza brevemente lo stato del mercato oggi. Rispondi in JSON: {'verdict': '...', 'reasoning': '...'}"
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json",
            safety_settings=[
                types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
            ]
        )
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        
        print("\n--- API RESPONSE ---")
        if response and response.text:
            print(response.text)
            print("\n✅ Verification Successful!")
        else:
            print("❌ Empty response from Google API.")
            print(f"Full response object: {response}")
            
    except Exception as e:
        print(f"\n❌ Error calling Google API: {e}")

if __name__ == "__main__":
    test_google_direct()
