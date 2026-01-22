"""
BG SAXO CSV Extractor (Direct LLM)
==================================
Reads the full CSV and uses Qwen (JSON Mode) to extract holdings.
"""
import requests
import json
import math
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:14b-instruct-q6_K"
CSV_FILE = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv")
OUTPUT_FILE = Path(r"d:\Download\Progetto WAR ROOM\warroom\data\extracted\BG_SAXO_Holdings_Final.json")

# Chunk size 
CHUNK_SIZE = 10

PROMPT_TEMPLATE = """You are a Data Processor.
Convert this CSV data into a JSON array of holdings.

COLUMN MAPPING:
- "Strumento" -> name (and ticker if contained, e.g. "Apple Inc")
- "Quantità" -> quantity (number)
- "Valuta" -> currency (ISO code)
- "Prz. corrente" -> current_price
- "Prezzo di apertura" -> cost_basis

RULES:
- Return ONLY JSON.
- Use the root key "holdings" for the array.
- Output format: {{ "holdings": [ {{ "name": "...", "quantity": 10, ... }} ] }}

CSV CONTENT:
{content}
"""

def call_llm(snippet):
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": PROMPT_TEMPLATE.format(content=snippet),
                "format": "json",  # Force JSON
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=300
        )
        if resp.status_code == 200:
            return json.loads(resp.json()['response'])
        print(f"Error {resp.status_code}: {resp.text}")
        return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def main():
    print(f"🚀 Processing: {CSV_FILE.name}")
    
    # Read all lines
    with open(CSV_FILE, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    # User logic: 
    # Row 1 (index 0): Header
    # Row 2 (index 1): Text (SKIP)
    # Row 3+ (index 2+): Data
    
    if len(lines) < 3:
        print("❌ File too short (< 3 lines)")
        return

    header = lines[0]
    data_lines = lines[2:] # Skip line 1
    
    print(f"📊 Header: {header.strip()[:50]}...")
    print(f"🗑️ Skipped Line 2: {lines[1].strip()[:50]}...")
    print(f"📦 Total Data Rows: {len(data_lines)}")
    
    all_holdings = []
    
    # Process in chunks
    num_chunks = math.ceil(len(data_lines) / CHUNK_SIZE)
    for i in range(num_chunks):
        start = i * CHUNK_SIZE
        end = start + CHUNK_SIZE
        chunk_lines = data_lines[start:end]
        
        snippet = header + "".join(chunk_lines)
        
        print(f"   ⏳ Processing Chunk {i+1}/{num_chunks} ({len(chunk_lines)} rows)...")
        result = call_llm(snippet)
        
        # Robust parsing for any plausible key
        found_items = []
        if result:
            for key in ["holdings", "positions", "portfolio", "data", "items"]:
                if key in result and isinstance(result[key], list):
                    found_items = result[key]
                    print(f"      ✅ Extracted {len(found_items)} items (key: '{key}')")
                    break
        
        if found_items:
            all_holdings.extend(found_items)
        else:
            print(f"      ❌ Failed chunk (Result keys: {list(result.keys()) if result else 'None'})")
            
    # Save Final Result
    final_output = {
        "broker": "BG_SAXO",
        "type": "HOLDINGS",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_items": len(all_holdings),
        "data": all_holdings
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print(f"\n💾 Saved to: {OUTPUT_FILE}")
    print(f"🎉 Total Holdings Extracted: {len(all_holdings)}")

if __name__ == "__main__":
    main()
