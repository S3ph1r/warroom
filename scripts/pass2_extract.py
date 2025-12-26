"""Pass 2: Extract ALL holdings using the structure from Pass 1"""
import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# The mapping from Pass 1
COLUMN_MAPPING = {
    "Strumento": "name",
    "Ticker": "ticker",
    "ISIN": "isin",
    "Quantita": "quantity",
    "Prezzo di apertura": "purchase_price",
    "Prz. corrente": "current_price",
    "Valuta": "currency",
    "Tipo attivita": "asset_type",
    "Valore di mercato (EUR)": "market_value"
}

# Load CSV
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine="python")
df.columns = [c.replace("\ufeff", "").replace('"', "").strip() for c in df.columns]

# Clean: remove summary rows (rows with NaN in key fields)
df_clean = df[df["Strumento"].notna() & (df["Strumento"] != "")].copy()

print("PASS 2: DATA EXTRACTION")
print("="*70)
print(f"Total rows after cleaning: {len(df_clean)}")
print()

# Select only mapped columns that exist
existing_cols = [c for c in COLUMN_MAPPING.keys() if c in df_clean.columns]
print(f"Using columns: {existing_cols}")

# Get data in chunks (20 rows at a time to not overwhelm Mistral)
CHUNK_SIZE = 20
all_holdings = []

for chunk_start in range(0, len(df_clean), CHUNK_SIZE):
    chunk = df_clean.iloc[chunk_start:chunk_start + CHUNK_SIZE]
    chunk_subset = chunk[existing_cols]
    chunk_md = chunk_subset.to_markdown(index=False)
    
    print(f"\nChunk {chunk_start//CHUNK_SIZE + 1}: rows {chunk_start+1}-{min(chunk_start+CHUNK_SIZE, len(df_clean))}")
    
    PROMPT = f"""Estrai i dati di questa tabella finanziaria.

MAPPATURA COLONNE:
{json.dumps(COLUMN_MAPPING, indent=2, ensure_ascii=False)}

DATI:
{chunk_md}

Estrai OGNI riga come oggetto JSON. Restituisci:
{{
  "holdings": [
    {{"name": "...", "ticker": "...", "isin": "...", "quantity": 0.0, "purchase_price": 0.0, "current_price": 0.0, "currency": "...", "asset_type": "..."}}
  ]
}}"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 4096}
        },
        timeout=180
    )
    
    if response.status_code == 200:
        result = response.json().get("response", "")
        try:
            data = json.loads(result)
            holdings = data.get("holdings", [])
            all_holdings.extend(holdings)
            print(f"  Extracted: {len(holdings)} holdings")
            
            # Show first 2 from this chunk
            for h in holdings[:2]:
                print(f"    - {h.get('name', 'N/A')[:25]} | {h.get('ticker')} | qty={h.get('quantity')}")
        except:
            print(f"  Parse error")
    else:
        print(f"  API error: {response.status_code}")

print()
print("="*70)
print(f"TOTAL EXTRACTED: {len(all_holdings)} holdings")
print("="*70)

# Save result
with open("scripts/pass2_extracted.json", "w", encoding="utf-8") as f:
    json.dump({"holdings": all_holdings}, f, indent=2, ensure_ascii=False)
print("Saved to: scripts/pass2_extracted.json")

# Show summary
print()
print("FIRST 10 HOLDINGS:")
for i, h in enumerate(all_holdings[:10], 1):
    name = str(h.get("name", "N/A"))[:25]
    ticker = str(h.get("ticker", ""))[:10]
    isin = str(h.get("isin", ""))
    qty = h.get("quantity", 0)
    price = h.get("purchase_price", 0)
    currency = h.get("currency", "")
    print(f"{i:2}. {name:<25} | {ticker:<10} | {isin} | {qty} @ {price} {currency}")
