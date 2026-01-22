"""
TWO-PASS EXTRACTION SYSTEM
==========================
Pass 1: Analyze document structure (headers, columns, data start)
Pass 2: Extract data using the discovered structure
"""
import pandas as pd
import json
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# ============================================================
# PASS 1: STRUCTURE ANALYSIS
# ============================================================
PROMPT_STRUCTURE = '''Sei un analizzatore di documenti finanziari. Analizza questa tabella e identifica la STRUTTURA.

OBIETTIVO: Capire il layout del documento, NON estrarre i dati.

RESTITUISCI un JSON con:
1. "columns": lista delle intestazioni colonne in ordine
2. "column_mapping": mappa da intestazione italiana a campo standard
3. "data_start_row": numero riga dove iniziano i dati (0-indexed)
4. "sample_row": una riga di esempio per verificare la struttura

CAMPI STANDARD DA MAPPARE:
- name (nome dello strumento)
- ticker (simbolo)
- isin (codice ISIN)
- quantity (quantità)
- purchase_price (prezzo di acquisto/apertura)
- current_price (prezzo corrente)
- currency (valuta)
- asset_type (tipo di asset)

DOCUMENTO:
{content}

Rispondi SOLO con JSON valido.'''

# ============================================================
# PASS 2: DATA EXTRACTION
# ============================================================
PROMPT_EXTRACT = '''Sei un estrattore di dati finanziari. Estrai i dati usando questa MAPPA STRUTTURA:

STRUTTURA DOCUMENTO:
{structure}

REGOLE:
- Usa ESATTAMENTE la mappatura colonne fornita
- Estrai TUTTE le righe di dati (escludi righe vuote o totali)
- Converti i numeri (es: "45,0" → 45.0)

DATI DA ESTRARRE:
{content}

Restituisci JSON con formato:
{{
  "holdings": [
    {{"name": "...", "ticker": "...", "isin": "...", "quantity": 0.0, "purchase_price": 0.0, "currency": "..."}}
  ]
}}'''

def call_mistral(prompt: str) -> str:
    """Call Mistral and return response."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 4096}
            },
            timeout=180
        )
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            print(f"API Error: {response.status_code}")
            return ""
    except Exception as e:
        print(f"Exception: {e}")
        return ""

def load_csv_sample(csv_path: str, sample_rows: int = 15) -> tuple[str, pd.DataFrame]:
    """Load CSV and return sample as markdown + full dataframe."""
    df = pd.read_csv(csv_path, sep=None, engine='python')
    df.columns = [c.replace('\ufeff', '').replace('"', '').strip() for c in df.columns]
    
    # Get sample including header row
    sample = df.head(sample_rows)
    sample_md = sample.to_markdown(index=False)
    
    return sample_md, df

def two_pass_extraction(csv_path: str):
    """Run two-pass extraction."""
    print("="*70)
    print("TWO-PASS EXTRACTION SYSTEM")
    print("="*70)
    
    # Load data
    sample_md, full_df = load_csv_sample(csv_path)
    print(f"\nLoaded: {len(full_df)} rows, {len(full_df.columns)} columns")
    
    # ========================================
    # PASS 1: Structure Analysis
    # ========================================
    print("\n" + "="*70)
    print("PASS 1: ANALYZING STRUCTURE")
    print("="*70)
    
    prompt1 = PROMPT_STRUCTURE.format(content=sample_md)
    print(f"Sending {len(prompt1)} chars to Mistral...")
    
    structure_response = call_mistral(prompt1)
    
    print("\nMistral Structure Analysis:")
    print("-"*50)
    print(structure_response[:1500] if len(structure_response) > 1500 else structure_response)
    
    # Parse structure
    try:
        structure = json.loads(structure_response)
        print("\n✓ Structure parsed successfully!")
        print(f"  Columns identified: {len(structure.get('columns', []))}")
        print(f"  Mappings: {structure.get('column_mapping', {})}")
    except json.JSONDecodeError as e:
        print(f"\n✗ Failed to parse structure: {e}")
        return None
    
    # ========================================
    # PASS 2: Data Extraction
    # ========================================
    print("\n" + "="*70)
    print("PASS 2: EXTRACTING DATA")
    print("="*70)
    
    # Use structure to extract full data
    # Take subset for speed (first 20 rows after cleaning)
    df_clean = full_df[full_df[full_df.columns[0]].notna()].head(20)
    data_md = df_clean.to_markdown(index=False)
    
    prompt2 = PROMPT_EXTRACT.format(
        structure=json.dumps(structure, indent=2, ensure_ascii=False),
        content=data_md
    )
    print(f"Sending {len(prompt2)} chars to Mistral...")
    
    extract_response = call_mistral(prompt2)
    
    print("\nMistral Extraction Result:")
    print("-"*50)
    
    # Parse extraction
    try:
        result = json.loads(extract_response)
        holdings = result.get('holdings', [])
        print(f"\n✓ Extracted {len(holdings)} holdings!")
        
        print("\nSample Holdings:")
        for i, h in enumerate(holdings[:5], 1):
            print(f"  {i}. {h.get('name', 'N/A')[:30]}")
            print(f"     Ticker: {h.get('ticker')} | ISIN: {h.get('isin')}")
            print(f"     Qty: {h.get('quantity')} @ {h.get('purchase_price')} {h.get('currency')}")
            
        return result
        
    except json.JSONDecodeError as e:
        print(f"\n✗ Failed to parse extraction: {e}")
        print(f"Raw response: {extract_response[:500]}")
        return None

if __name__ == "__main__":
    csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
    result = two_pass_extraction(csv_path)
    
    if result:
        # Save result
        output_path = Path(__file__).parent / "two_pass_result.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to: {output_path}")
