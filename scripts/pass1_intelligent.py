"""
PASS 1 INTELLIGENT: Deep Document Structure Analysis
=====================================================
Mistral deve:
1. Analizzare i TIPI DI DATI in ogni colonna (testo vs numeri)
2. Identificare le righe (header, dati, sommario)
3. Capire la struttura del documento
4. Mappare le colonne basandosi sul CONTENUTO, non solo sul nome
"""
import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# Load CSV
csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
df = pd.read_csv(csv_path, sep=None, engine="python")
df.columns = [c.replace("\ufeff", "").replace('"', "").strip() for c in df.columns]

print("PASS 1 INTELLIGENT: ANALISI STRUTTURA PROFONDA")
print("="*70)

# Prepare analysis data for Mistral
# Show column names + sample values + data types
analysis = []
for col in df.columns[:15]:  # First 15 columns
    sample_vals = df[col].dropna().head(3).tolist()
    # Detect if numeric or text
    try:
        numeric = pd.to_numeric(df[col].dropna().head(5), errors='coerce').notna().all()
    except:
        numeric = False
    
    analysis.append({
        "colonna": col,
        "tipo_dati": "NUMERO" if numeric else "TESTO",
        "esempi": [str(v)[:30] for v in sample_vals]
    })

analysis_text = json.dumps(analysis, indent=2, ensure_ascii=False)

# Show first few COMPLETE rows to help Mistral understand structure
sample_rows = df.head(5).to_dict('records')
sample_text = json.dumps(sample_rows[:3], indent=2, ensure_ascii=False, default=str)

print(f"Colonne analizzate: {len(analysis)}")
print()
print("STRUTTURA COLONNE (primi 10):")
for a in analysis[:10]:
    print(f"  {a['colonna']:<25} | {a['tipo_dati']:<6} | Es: {a['esempi'][0] if a['esempi'] else 'N/A'}")
print()

# Intelligent prompt that asks Mistral to UNDERSTAND the data
PROMPT = f"""Sei un analizzatore di documenti finanziari intelligente.

OBIETTIVO: Capire la STRUTTURA dei dati, non solo i nomi delle colonne.

ANALISI COLONNE (nome, tipo dati, esempi):
{analysis_text}

PRIME 3 RIGHE COMPLETE:
{sample_text}

TASK:
1. Identifica QUALE colonna contiene cosa basandoti sui VALORI:
   - name: contiene TESTO con nomi di aziende/asset (es: "Apple Inc", "NVIDIA Corp")
   - ticker: contiene simboli brevi (es: "AAPL", "NVDA", "ETL:xpar")
   - isin: codice 12 caratteri che inizia con paese (es: "US0378331005", "FR0010221234")
   - quantity: NUMERO che rappresenta pezzi posseduti (es: 10, 45, 100)
   - purchase_price: NUMERO decimale prezzo acquisto (es: 150.50, 2.89)
   - current_price: NUMERO decimale prezzo corrente
   - currency: codice valuta 3 lettere (EUR, USD, DKK)

2. Identifica le righe:
   - Quale riga e' l'header?
   - Da quale riga iniziano i dati degli asset?
   - Ci sono righe di sommario/totale da ignorare?

Rispondi con JSON:
{{
  "document_structure": {{
    "header_row": 0,
    "data_start_row": 1,
    "summary_rows": [],
    "rows_per_asset": 1
  }},
  "column_analysis": {{
    "name_column": "nome esatto colonna che contiene nomi asset",
    "ticker_column": "nome esatto colonna ticker",
    "isin_column": "nome esatto colonna ISIN",
    "quantity_column": "nome esatto colonna quantita",
    "purchase_price_column": "nome esatto colonna prezzo acquisto",
    "currency_column": "nome esatto colonna valuta"
  }},
  "validation": {{
    "first_asset_name": "nome del primo asset trovato",
    "first_asset_ticker": "ticker del primo asset",
    "first_asset_isin": "ISIN del primo asset",
    "first_asset_qty": 0.0
  }}
}}"""

print("Calling Mistral per analisi intelligente...")
print(f"Prompt: {len(PROMPT)} chars")
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
print("MISTRAL ANALYSIS:")
print("-"*70)
result = response.json().get("response", "")
print(result)
print("-"*70)

try:
    data = json.loads(result)
    print()
    print("STRUTTURA DOCUMENTO:")
    struct = data.get("document_structure", {})
    print(f"  Header row: {struct.get('header_row')}")
    print(f"  Data start: {struct.get('data_start_row')}")
    print(f"  Rows per asset: {struct.get('rows_per_asset')}")
    
    print()
    print("MAPPATURA COLONNE:")
    cols = data.get("column_analysis", {})
    for k, v in cols.items():
        print(f"  {k}: {v}")
    
    print()
    print("VALIDAZIONE (primo asset):")
    val = data.get("validation", {})
    for k, v in val.items():
        print(f"  {k}: {v}")
        
    # Save for Pass 2
    with open("scripts/pass1_structure.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print()
    print("Saved to: scripts/pass1_structure.json")
    
except Exception as e:
    print(f"Parse error: {e}")
