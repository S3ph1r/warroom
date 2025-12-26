"""
COMPREHENSIVE BG SAXO EXTRACTION DEBUG
1. Show what we're sending to Mistral
2. Show exact Mistral response
3. Diagnose the failure
"""
import pandas as pd
import json
import requests

# ============================================================
# STEP 1: LOAD AND CLEAN CSV
# ============================================================
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine='python')

# Clean column names
df.columns = [c.replace('\ufeff', '').replace('"', '').strip() for c in df.columns]

# Drop summary rows (first row appears to be totals with NaN in key fields)
df_clean = df[df['Strumento'].notna() & (df['Strumento'] != '')].copy()

print("="*70)
print("STEP 1: CSV DATA LOADED")
print("="*70)
print(f"Total rows (after cleaning): {len(df_clean)}")
print(f"Key columns available: Strumento, Quantità, Prezzo di apertura, ISIN, Ticker, Valuta")
print()

# Show first 5 data rows with key columns
key_cols = ['Strumento', 'Valuta', 'Quantità', 'Prezzo di apertura', 'ISIN', 'Ticker', 'Tipo attività']
existing_cols = [c for c in key_cols if c in df_clean.columns]
print("SAMPLE DATA (First 5 Holdings):")
print(df_clean[existing_cols].head().to_string())

# ============================================================
# STEP 2: PREPARE CHUNK FOR MISTRAL
# ============================================================
print()
print("="*70)
print("STEP 2: PREPARING CHUNK FOR MISTRAL")
print("="*70)

# Take first 10 rows as a test chunk
chunk = df_clean.head(10)
chunk_md = chunk[existing_cols].to_markdown(index=False)

print(f"Chunk size: {len(chunk)} rows")
print(f"Markdown length: {len(chunk_md)} chars")
print()
print("MARKDOWN CONTENT TO SEND:")
print("-"*70)
print(chunk_md)
print("-"*70)

# ============================================================
# STEP 3: BUILD PROMPT
# ============================================================
print()
print("="*70)
print("STEP 3: PROMPT TO SEND")
print("="*70)

PROMPT = '''Sei un parser di dati finanziari. Analizza questa tabella di posizioni (holdings) da BG SAXO.

ESTRAI i seguenti campi per ogni riga:
- name: Nome dello strumento
- ticker: Simbolo ticker  
- isin: Codice ISIN
- quantity: Quantità posseduta (numero)
- purchase_price: Prezzo di acquisto (numero, dalla colonna "Prezzo di apertura")
- currency: Valuta

Restituisci SOLO un JSON valido con questo formato:
{
  "holdings": [
    {"name": "...", "ticker": "...", "isin": "...", "quantity": 100.0, "purchase_price": 50.25, "currency": "EUR"}
  ]
}

TABELLA DATI:
''' + chunk_md

print(f"Total prompt length: {len(PROMPT)} chars")
print()
print("PROMPT PREVIEW (first 500 chars):")
print(PROMPT[:500])
print("...")

# ============================================================
# STEP 4: CALL MISTRAL
# ============================================================
print()
print("="*70)
print("STEP 4: CALLING MISTRAL")
print("="*70)

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral-nemo:latest",
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 2048}
        },
        timeout=120
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        result = response.json()
        raw_response = result.get("response", "")
        print("RAW MISTRAL RESPONSE:")
        print("-"*70)
        print(raw_response[:2000] if len(raw_response) > 2000 else raw_response)
        print("-"*70)
        
        # Try to parse JSON
        try:
            data = json.loads(raw_response)
            print()
            print("JSON PARSED SUCCESSFULLY!")
            print(f"Holdings extracted: {len(data.get('holdings', []))}")
            for h in data.get('holdings', [])[:3]:
                print(f"  - {h.get('name')}: {h.get('quantity')} @ {h.get('purchase_price')} {h.get('currency')}")
        except json.JSONDecodeError as e:
            print()
            print(f"JSON PARSE ERROR: {e}")
    else:
        print(f"API ERROR: {response.text}")
        
except Exception as e:
    print(f"EXCEPTION: {e}")

print()
print("="*70)
print("ANALYSIS COMPLETE")
print("="*70)
