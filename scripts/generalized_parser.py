"""
GENERALIZED DOCUMENT PARSER
===========================
Mistral analyzes document structure and generates pandas extraction instructions.
Works for ANY document format: CSV, PDF tables, multi-row assets, mixed content.

FLOW:
1. Mistral analyzes raw document -> outputs extraction INSTRUCTIONS
2. Python/Pandas follows instructions -> outputs clean data
3. Clean data -> ready for DB
"""
import json
import requests
import pandas as pd
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

def get_document_preview(file_path: str, max_lines: int = 20) -> str:
    """Get raw text preview of document for Mistral analysis."""
    path = Path(file_path)
    
    if path.suffix.lower() == '.csv':
        with open(path, 'r', encoding='utf-8-sig') as f:
            lines = []
            for i, line in enumerate(f):
                if i < max_lines:
                    lines.append(f"LINE {i}: {line.strip()[:200]}")
                else:
                    break
        return "\n".join(lines)
    else:
        # For other file types, add handlers
        return f"Unsupported file type: {path.suffix}"

def ask_mistral_for_instructions(document_preview: str) -> dict:
    """
    Mistral analyzes document and returns extraction instructions for pandas.
    """
    
    PROMPT = f"""Sei un analizzatore di documenti finanziari. Devi capire la STRUTTURA del documento e generare ISTRUZIONI per l'estrazione dei dati.

DOCUMENTO (prime righe):
{document_preview}

ANALIZZA:
1. Quale riga contiene l'HEADER della tabella? (numero riga)
2. Ci sono righe di SOMMARIO o TITOLO da saltare? (lista numeri riga)
3. Da quale riga iniziano i DATI degli asset? (numero riga)
4. Quante righe occupa OGNI asset? (1, 2, o piu?)
5. Quali colonne contengono i dati che ci servono?

RESTITUISCI istruzioni JSON per pandas:
{{
  "file_type": "csv",
  "encoding": "utf-8-sig",
  "instructions": {{
    "header_row": 0,
    "skip_rows": [1],
    "data_start_row": 2,
    "rows_per_asset": 1
  }},
  "column_mapping": {{
    "0": "name",
    "1": "direction",
    "2": "currency",
    "3": "quantity",
    "4": "purchase_price"
  }},
  "column_names": {{
    "name": "Strumento",
    "currency": "Valuta",
    "quantity": "Quantita",
    "purchase_price": "Prezzo di apertura"
  }},
  "validation": {{
    "expected_assets": 48,
    "first_asset_name": "nome primo asset",
    "sample_values": {{
      "name": "Eutelsat Communications",
      "quantity": 45,
      "purchase_price": 2.89
    }}
  }}
}}

IMPORTANTE: 
- Guarda i VALORI nelle righe per capire cosa sono (nomi=testo, qty=numeri interi, prezzi=decimali)
- Se vedi righe tipo "Azioni (48)" sono SOMMARI da saltare
- Restituisci SOLO il JSON, nessun altro testo"""

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
    
    if response.status_code == 200:
        result = response.json().get("response", "")
        try:
            return json.loads(result)
        except:
            return {"error": "Failed to parse JSON", "raw": result}
    else:
        return {"error": f"API error: {response.status_code}"}

def extract_with_instructions(file_path: str, instructions: dict) -> list:
    """
    Use pandas to extract data following Mistral's instructions.
    """
    inst = instructions.get("instructions", {})
    col_map = instructions.get("column_mapping", {})
    col_names = instructions.get("column_names", {})
    
    # Read CSV with instructions
    df = pd.read_csv(
        file_path,
        encoding=instructions.get("encoding", "utf-8-sig"),
        skiprows=inst.get("skip_rows", []),
        on_bad_lines='skip'  # Skip malformed rows
    )
    
    # Clean column names
    df.columns = [c.replace('\ufeff', '').replace('"', '').strip() for c in df.columns]
    
    # Extract data using column names
    holdings = []
    for _, row in df.iterrows():
        # Skip empty rows
        if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == "":
            continue
            
        holding = {}
        for field, col_name in col_names.items():
            if col_name in df.columns:
                val = row[col_name]
                # Convert to appropriate type
                if field in ['quantity', 'purchase_price', 'current_price', 'market_value']:
                    try:
                        holding[field] = float(val) if pd.notna(val) else 0.0
                    except:
                        holding[field] = 0.0
                else:
                    holding[field] = str(val) if pd.notna(val) else ""
        
        if holding.get('name'):
            holdings.append(holding)
    
    return holdings

def process_document(file_path: str):
    """Main function: Mistral analyzes, Pandas extracts."""
    
    print("="*70)
    print("GENERALIZED DOCUMENT PARSER")
    print("="*70)
    print(f"File: {file_path}")
    print()
    
    # Step 1: Get document preview
    print("STEP 1: Reading document preview...")
    preview = get_document_preview(file_path)
    print(preview[:500])
    print()
    
    # Step 2: Ask Mistral for instructions
    print("STEP 2: Asking Mistral for extraction instructions...")
    instructions = ask_mistral_for_instructions(preview)
    print(json.dumps(instructions, indent=2, ensure_ascii=False))
    print()
    
    if "error" in instructions:
        print(f"ERROR: {instructions['error']}")
        return None
    
    # Step 3: Extract with pandas using instructions
    print("STEP 3: Extracting data with pandas...")
    holdings = extract_with_instructions(file_path, instructions)
    print(f"Extracted: {len(holdings)} holdings")
    print()
    
    # Step 4: Show sample
    print("SAMPLE (first 5):")
    for i, h in enumerate(holdings[:5], 1):
        print(f"  {i}. {h.get('name', 'N/A')[:30]} | qty={h.get('quantity')} | price={h.get('purchase_price')}")
    
    # Save result
    output_path = Path(file_path).stem + "_extracted.json"
    with open(f"scripts/{output_path}", "w", encoding="utf-8") as f:
        json.dump({"holdings": holdings, "instructions": instructions}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: scripts/{output_path}")
    
    return holdings

if __name__ == "__main__":
    # Test with BG SAXO CSV
    csv_path = r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv"
    holdings = process_document(csv_path)
