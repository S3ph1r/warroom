"""
Test: Simplified Prompt + JSON Mode
"""
import requests
import json
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:14b-instruct-q6_K"
CSV_FILE = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv")

# Read first 15 lines only
def read_snippet(filepath, lines=15):
    content = ""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for _ in range(lines):
            content += f.readline()
    return content

# Simple prompt
PROMPT = """Converti questo CSV in un array JSON. 
Ogni riga diventa un oggetto con le chiavi prese dall'header.
Rispondi SOLO con JSON valido, nessun testo.

CSV:
{csv_content}
"""

def main():
    print(f"📄 File: {CSV_FILE.name}")
    
    snippet = read_snippet(CSV_FILE)
    print(f"📋 Snippet ({len(snippet)} chars):")
    print(snippet[:500])
    print("...")
    
    prompt = PROMPT.format(csv_content=snippet)
    
    print(f"\n🤖 Calling {MODEL} with JSON MODE...")
    
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "format": "json",  # FORCE JSON OUTPUT
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=180
        )
        
        if resp.status_code == 200:
            result = resp.json()
            response_text = result.get('response', '')
            
            print(f"\n📨 Response length: {len(response_text)} chars")
            print("\n--- RESPONSE (first 2000 chars) ---")
            print(response_text[:2000])
            
            # Try to parse as JSON
            try:
                parsed = json.loads(response_text)
                print("\n✅ VALID JSON!")
                print(f"Type: {type(parsed)}")
                if isinstance(parsed, list):
                    print(f"Items: {len(parsed)}")
                    print("First item:", json.dumps(parsed[0], indent=2, ensure_ascii=False) if parsed else "empty")
                elif isinstance(parsed, dict):
                    print(f"Keys: {list(parsed.keys())}")
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON Parse Error: {e}")
        else:
            print(f"❌ HTTP Error: {resp.status_code}")
            print(resp.text[:500])
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
