"""
Debug script for BG SAXO extraction with Mistral.
Implements Chunking and Broker-Specific Prompting.
"""
import sys
import json
import logging
from pathlib import Path
import pandas as pd
import requests

# Helper to import from services if needed, but we'll self-contain for debug
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"
CSV_PATH = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"

# Specialized Prompt
PROMPT_SAXO = """
Sei un assistente finanziario. Analizza la seguente tabella delle posizioni (holdings) di BG SAXO.
Estrai i dati in formato JSON.

MAPPING COLONNE:
- "Strumento" o "Instrument" -> name / ticker
- "Isin" -> isin (se presente)
- "Quantità" o "Quantity" -> quantity
- "Prezzo di apertura" o "Open Price" -> purchase_price
- "Valuta" -> currency
- "Valore" -> current_value

REGOLE:
- Ignora righe vuote o totali.
- Se l'ISIN è nel nome (es. "Apple (US...)", estrailo se possibile, altrimenti usa null).
- Restituisci SOLO il JSON valido.

JSON OUTPUT FORMAT:
{{
  "holdings": [
    {{
      "name": "Nome Strumento",
      "isin": "US1234567890",
      "quantity": 10.0,
      "purchase_price": 100.50,
      "currency": "EUR"
    }}
  ]
}}

---
DATI (Tabella Markdown):
{content}
"""

def get_markdown_chunks(csv_path, chunk_size=30):
    """
    Reads CSV and yields markdown chunks (Header + N rows).
    """
    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        # Clean columns
        df.columns = [c.replace('ï»¿', '').strip() for c in df.columns]
        
        print(f"Loaded DataFrame: {len(df)} rows. Columns: {list(df.columns)}")
        
        header_df = df.iloc[:0] # Empty df with headers
        
        # Generator for chunks
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i : i+chunk_size]
            # Convert to markdown
            md = chunk.to_markdown(index=False)
            yield md, i, len(df)
            
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

def call_mistral(content):
    prompt = PROMPT_SAXO.format(content=content)
    # print(f"\n--- PROMPT (Preview) ---\n{prompt[:500]}...\n------------------------\n")
    
    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0}
            },
            timeout=120
        )
        if res.status_code == 200:
            return res.json().get("response")
        else:
            return f"Error: {res.status_code} {res.text}"
    except Exception as e:
        return f"Exception: {e}"

def run_debug():
    print(f"Target File: {CSV_PATH}")
    
    chunks = get_markdown_chunks(CSV_PATH, chunk_size=20) # Small chunk for testing
    
    # Process First Chunk Only
    for md_content, start_row, total in chunks:
        print(f"\nProcessing Chunk {start_row}-{start_row+20} of {total}...")
        print("MD Content Preview:")
        print(md_content[:500])
        
        response = call_mistral(md_content)
        
        print("\n--- MISTRAL RESPONSE ---")
        print(response)
        
        # Verify JSON
        try:
            data = json.loads(response)
            print(f"\nExtracted {len(data.get('holdings', []))} items.")
        except:
            print("\nFailed to parse JSON.")
        
        break # STOP after first chunk for debug

if __name__ == "__main__":
    run_debug()
