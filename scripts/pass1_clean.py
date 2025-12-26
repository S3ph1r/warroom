"""Pass 1: Structure Analysis - Clean version without Unicode issues"""
import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# Load CSV
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine="python")
df.columns = [c.replace("\ufeff", "").replace('"', "").strip() for c in df.columns]

# Get first 5 rows, key columns
key_cols = ["Strumento", "Long/Short", "Valuta", "Quantita", "Prezzo di apertura", "ISIN", "Ticker", "Tipo attivita"]
existing = [c for c in key_cols if c in df.columns]
sample = df.head(5)[existing]
sample_md = sample.to_markdown(index=False)

print("PASS 1: STRUCTURE ANALYSIS")
print("="*60)
print(f"Columns found: {existing}")
print(f"Sample rows: 5, chars: {len(sample_md)}")
print()
print("SAMPLE DATA:")
print(sample_md)
print()

PROMPT = """Analizza questa tabella finanziaria e identifica le colonne.

TABELLA:
""" + sample_md + """

Rispondi con JSON che mappa ogni colonna al campo standard:
{
  "column_mapping": {
    "Strumento": "name",
    "Quantita": "quantity"
  },
  "sample_asset": "nome del primo asset"
}

Campi standard: name, ticker, isin, quantity, purchase_price, current_price, currency, asset_type"""

print("Calling Mistral...")
print()

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

print(f"Status: {response.status_code}")
print()
print("MISTRAL RESPONSE:")
print("-"*60)
result = response.json().get("response", "")
print(result)
print("-"*60)

try:
    data = json.loads(result)
    print()
    print("PARSED OK!")
    print("Column mapping:")
    for k, v in data.get("column_mapping", {}).items():
        print(f"  {k} -> {v}")
    print(f"Sample asset: {data.get('sample_asset', 'N/A')}")
except Exception as e:
    print(f"Parse error: {e}")
