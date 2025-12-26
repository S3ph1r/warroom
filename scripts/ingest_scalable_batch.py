"""
SCALABLE CAPITAL BATCH INGESTION
================================
Orchestrates the ingestion of Scalable Capital documents.
1. Financial Status -> Holdings Extraction
2. Monthly Statements -> Transactions Extraction (Mistral Loop)
3. Reconciliation
"""
import sys
import os
import json
from pathlib import Path
from extract_all_transactions import run_extraction as run_mistral_loop

# Import the classification/extraction logic from generalized parser (simulating imports or re-implementing for simplicity in this batch script)
# To be robust, we'll use a simplified version here for "Financial Status"
import fitz
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

DIR_PATH = r"D:\Download\SCALABLE CAPITAL"
HOLDINGS_OUT = "scripts/scalable_holdings.json"
TRANSACTIONS_OUT = "scripts/scalable_transactions_full.json"

def extract_holdings_from_pdf_simple(pdf_path):
    """
    Extract Holdings from Scalable Status PDF.
    Since it's short, we can dump text and ask Mistral in one go.
    """
    print(f"Extracting Holdings from {Path(pdf_path).name}...")
    doc = fitz.open(pdf_path)
    text = ""
    for p in doc:
        text += p.get_text("text") + "\n"
    
    PROMPT = f"""Estrai le posizioni (HOLDINGS) da questo report Scalable Capital.

TESTO:
{text[:4000]} (truncated)

Estrai lista JSON:
{{
  "holdings": [
    {{
      "name": "Nome Asset",
      "isin": "ISIN",
      "quantity": 10.0,
      "market_value": 1500.50,
      "currency": "EUR"
    }}
  ]
}}"""
    
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": MODEL, "prompt": PROMPT, "stream": False, "format": "json"
    })
    
    if response.status_code == 200:
        data = json.loads(response.json().get("response", "{}"))
        return data
    return {"holdings": []}

def run_batch():
    print("SCALABLE CAPITAL BATCH INGESTION")
    print("="*50)
    
    files = list(Path(DIR_PATH).glob("*.pdf"))
    print(f"Found {len(files)} files.")
    
    # 1. Identify files
    holdings_file = None
    txn_files = []
    
    for f in files:
        name = f.name.lower()
        if "financial status" in name:
            holdings_file = f
        elif "statement" in name:
            txn_files.append(f)
            
    # 2. Extract Holdings
    if holdings_file:
        data = extract_holdings_from_pdf_simple(holdings_file)
        with open(HOLDINGS_OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved {len(data.get('holdings', []))} holdings to {HOLDINGS_OUT}")
    else:
        print("No Holdings file found!")

    # 3. Extract Transactions (Loop)
    all_txns = []
    for tf in txn_files:
        print(f"\nProcessing Statement: {tf.name}")
        # We reuse the mistral loop logic but tailored per file
        # Creating a temp output for this file to avoid overwrite collisions if running parallel, 
        # but here we run serial.
        
        # We append to memory `all_txns`
        file_txns = run_mistral_loop(str(tf), f"scripts/temp_{tf.name}.json")
        all_txns.extend(file_txns)
        
    # Save full transaction history
    with open(TRANSACTIONS_OUT, "w", encoding="utf-8") as f:
        json.dump({"transactions": all_txns}, f, indent=2)
    print(f"\nTotal Transactions extracted: {len(all_txns)}")
    
    # 4. Reconcile
    if Path(HOLDINGS_OUT).exists() and Path(TRANSACTIONS_OUT).exists():
        print("\nRunning Reconciliation...")
        import subprocess
        subprocess.run([
            sys.executable, "scripts/reconciliation_engine.py",
            "--holdings", HOLDINGS_OUT,
            "--transactions", TRANSACTIONS_OUT
        ]) 

if __name__ == "__main__":
    run_batch()
