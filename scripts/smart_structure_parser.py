"""
Smart Structure Parser
======================
Step 1: AI (Mistral) determines document structure (headers, delimiter, column map)
Step 2: Deterministic code (Pandas) uses that structure to extract data accurately
"""
import os
import sys
import json
import requests
import pandas as pd
import io
from pathlib import Path
from datetime import datetime

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")
INPUT_FOLDER = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")
OUTPUT_FOLDER = Path(__file__).resolve().parent.parent / 'data' / 'extracted'
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

PROMPT_STRUCTURE = """You are a Data Engineer. Analyze this file snippet (first few lines) to determine how to parse it.

TASK:
1. Identify DOCUMENT_TYPE: "HOLDINGS" (portfolio positions), "TRANSACTIONS" (history), or "OTHER".
2. Identify CSV PARSING RULES:
   - delimiter: The character separating values (e.g. ";", ",", "\t")
   - header_row: The 0-based index of the row containing column names
   - data_start_row: The 0-based index where actual data starts

3. Map the column names found in the file to these STANDARD fields:
   - ticker (Required, e.g. Symbol, Stock, ISIN)
   - isin (Optional)
   - quantity (Required, amount owned)
   - currency (Required, e.g. EUR, USD)
   - purchase_price (Optional, avg cost)
   - current_value (Optional, market val)

Return ONLY valid JSON (no markdown):
{{
  "document_type": "HOLDINGS",
  "parsing_config": {{
    "delimiter": ";",
    "header_row": 0,
    "data_start_row": 1
  }},
  "column_mapping": {{
    "ticker": "Strumento",
    "isin": "ISIN",
    "quantity": "Quantità",
    "currency": "Valuta",
    "purchase_price": "Prezzo medio",
    "current_value": "Valore di mercato"
  }}
}}

---
FILE SNIPPET:
{file_content}
"""

def get_file_snippet(filepath, lines=30):
    """Read first N lines of file for analysis."""
    snippet = ""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for _ in range(lines):
                snippet += f.readline()
    except Exception as e:
        return f"Error reading file: {e}"
    return snippet

def call_mistral(prompt):
    """Ask Mistral for the structure."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json().get('response', '')
        return f"Error: {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"

def extract_json(response_text):
    """Extract JSON object from response."""
    import re
    try:
        # Clean markdown
        text = re.sub(r'```json\s*', '', response_text)
        text = re.sub(r'```\s*', '', text)
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"JSON Parse Error: {e}")
    return None

def parse_with_config(filepath, config, mapping):
    """Use the AI-derived config to parse the full file deterministically."""
    print(f"\n--- DETERMINISTIC PARSING ---")
    print(f"Config: {config}")
    print(f"Mapping: {mapping}")
    
    try:
        df = pd.read_csv(
            filepath,
            sep=config.get('delimiter', ','),
            header=config.get('header_row', 0),
            encoding='utf-8',
            on_bad_lines='skip'
        )
        
        # Rename columns based on mapping
        # Swap mapping: {standard: actual} -> {actual: standard}
        rename_map = {v: k for k, v in mapping.items() if v in df.columns}
        df_renamed = df.rename(columns=rename_map)
        
        # Keep only mapped standard columns
        standard_cols = [k for k in mapping.keys()]
        available_cols = [c for c in df_renamed.columns if c in standard_cols]
        
        final_df = df_renamed[available_cols]
        
        # Clean numeric data (replace comma with dot for European formats)
        for col in ['quantity', 'purchase_price', 'current_value']:
            if col in final_df.columns:
                final_df[col] = final_df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
                
        return final_df
        
    except Exception as e:
        print(f"Parsing Failed: {e}")
        return None

def main():
    # 1. Select File
    files = sorted(INPUT_FOLDER.glob('*.csv'))
    if not files:
        print("No CSV files found.")
        return
        
    target_file = files[0] # Focus on first file
    print(f"TARGET: {target_file.name}")
    
    # 2. Get Snippet & Ask AI
    print("\n[1/3] extracting structure with Mistral...")
    snippet = get_file_snippet(target_file)
    prompt = PROMPT_STRUCTURE.format(file_content=snippet)
    
    ai_response = call_mistral(prompt)
    structure_info = extract_json(ai_response)
    
    if not structure_info:
        print("❌ Failed to get valid JSON from Mistral.")
        print("Raw Response:", ai_response[:500])
        return

    print("✅ Structure Detected:")
    print(json.dumps(structure_info, indent=2))
    
    # 3. Deterministic Parse
    if structure_info.get('document_type') == 'HOLDINGS':
        print("\n[2/3] Parsing content...")
        df = parse_with_config(
            target_file, 
            structure_info['parsing_config'], 
            structure_info['column_mapping']
        )
        
        if df is not None:
            print(f"\n[3/3] Success! Validated Data ({len(df)} rows):")
            print(df.head().to_string())
            
            # Save Result
            out_name = f"PARSED_{target_file.stem}.json"
            out_path = OUTPUT_FOLDER / out_name
            df.to_json(out_path, orient='records', indent=2)
            print(f"\nSaved to: {out_path}")
            
    else:
        print("Document identified as NOT Holdings - Skipping extraction.")

if __name__ == "__main__":
    main()
