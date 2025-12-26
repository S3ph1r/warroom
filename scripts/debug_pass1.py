"""
DEBUG PASS 1: Structure Analysis
See exactly what we send and what Mistral responds.
"""
import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# Load CSV
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine='python')
df.columns = [c.replace('\ufeff', '').replace('"', '').strip() for c in df.columns]

# Get just first 5 rows as sample (smaller = clearer for Mistral)
sample = df.head(5)

# Select only key columns to reduce complexity
key_cols = ['Strumento', 'Long/Short', 'Valuta', 'Quantità', 'Prezzo di apertura', 
            'Prz. corrente', 'ISIN', 'Ticker', 'Tipo attività']
existing = [c for c in key_cols if c in df.columns]
sample_slim = sample[existing]
sample_md = sample_slim.to_markdown(index=False)

print("="*70)
print("PASS 1 DEBUG: STRUCTURE ANALYSIS")
print("="*70)
print(f"\nCSV: {len(df)} rows, selected {len(existing)} columns")
print(f"Sample rows: {len(sample_slim)}")
print()

# Simplified prompt - just ask for column mapping
PROMPT = f'''Analizza questa tabella finanziaria e identifica le colonne.

TABELLA:
{sample_md}

Rispondi con un JSON che mappa ogni colonna italiana al campo standard:
- name = nome strumento
- ticker = simbolo ticker  
- isin = codice ISIN
- quantity = quantità
- purchase_price = prezzo acquisto/apertura
- current_price = prezzo corrente
- currency = valuta
- asset_type = tipo asset

Formato risposta:
{{
  "column_mapping": {{
    "Strumento": "name",
    "Quantità": "quantity",
    ...
  }},
  "total_columns": 9,
  "sample_asset": "primo nome asset nella tabella"
}}'''

print("PROMPT SENT TO MISTRAL:")
print("-"*70)
print(PROMPT)
print("-"*70)
print(f"\nPrompt length: {len(PROMPT)} chars")
print("\nCalling Mistral...")

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 1024}
    },
    timeout=120
)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    result = response.json().get("response", "")
    print("\nMISTRAL RESPONSE:")
    print("-"*70)
    print(result)
    print("-"*70)
    
    # Try to parse
    try:
        data = json.loads(result)
        print("\n✓ Valid JSON!")
        print(f"  Column mapping: {data.get('column_mapping', {})}")
        print(f"  Sample asset: {data.get('sample_asset', 'N/A')}")
    except:
        print("\n✗ Failed to parse JSON")
else:
    print(f"Error: {response.text}")
