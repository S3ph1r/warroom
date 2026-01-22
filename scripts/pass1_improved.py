"""Pass 1 IMPROVED: Get complete column mapping with all required fields"""
import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# Load CSV with ALL columns
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine="python")
df.columns = [c.replace("\ufeff", "").replace('"', "").strip() for c in df.columns]

# Show ALL column names first
print("PASS 1 IMPROVED: COMPLETE STRUCTURE ANALYSIS")
print("="*70)
print(f"Total columns in CSV: {len(df.columns)}")
print()
print("ALL COLUMN NAMES:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2}. {col}")
print()

# Get sample with more columns
sample = df.head(3)
sample_md = sample.to_markdown(index=False)

print(f"Sample: 3 rows, {len(sample_md)} chars")
print()

# More explicit prompt that lists all columns
column_list = ", ".join(df.columns)

PROMPT = f"""Sei un analizzatore di dati finanziari. Devi mappare TUTTE le colonne di questa tabella.

COLONNE PRESENTI NEL FILE:
{column_list}

TABELLA ESEMPIO:
{sample_md}

CAMPI DA MAPPARE (trova la colonna corrispondente per OGNUNO):
1. name = nome dello strumento/asset
2. ticker = simbolo ticker di borsa 
3. isin = codice ISIN (inizia con lettere paese, es: US, IT, FR)
4. quantity = quantita posseduta (numero di pezzi/azioni)
5. purchase_price = prezzo di acquisto/apertura
6. current_price = prezzo corrente
7. currency = valuta (EUR, USD, etc)
8. asset_type = tipo asset (Azione, ETF, etc)
9. market_value = valore di mercato

Rispondi SOLO con questo JSON esatto:
{{
  "column_mapping": {{
    "nome_colonna_italiana": "campo_standard",
    "altra_colonna": "altro_campo"
  }},
  "columns_found": 9,
  "sample_row": {{
    "name": "valore primo asset",
    "ticker": "simbolo",
    "isin": "codice",
    "quantity": 0.0
  }}
}}"""

print("Calling Mistral with improved prompt...")
print(f"Prompt length: {len(PROMPT)} chars")
print()

response = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": MODEL,
        "prompt": PROMPT,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 2048}
    },
    timeout=180
)

print(f"Status: {response.status_code}")
print()
print("MISTRAL RESPONSE:")
print("-"*70)
result = response.json().get("response", "")
print(result)
print("-"*70)

try:
    data = json.loads(result)
    print()
    print("COLUMN MAPPING COMPLETO:")
    mapping = data.get("column_mapping", {})
    for k, v in mapping.items():
        print(f"  {k:<30} -> {v}")
    print()
    print(f"Columns found: {data.get('columns_found', 'N/A')}")
    print(f"Sample row: {data.get('sample_row', {})}")
except Exception as e:
    print(f"Parse error: {e}")
