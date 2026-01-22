"""
REVOLUT BATCH INGESTION (UPDATED)
=================================
Targets:
- Trading Account Statement (Stocks)
- Crypto Account Statement (Crypto)
"""
import sys
import json
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

WORK_DIR = Path(r"D:\Download\Progetto WAR ROOM\warroom\scripts")
SOURCE_DIR = Path(r"D:\Download\Revolut")

def run_mistral_loop(pdf_path, output_name):
    output_file = WORK_DIR / output_name
    script_path = WORK_DIR / "extract_all_transactions.py"
    cmd = [
        str(Path(sys.executable)),
        str(script_path),
        "--pdf", str(pdf_path),
        "--output", str(output_file)
    ]
    
    # Cleanup stale progress
    progress_file = WORK_DIR / "progress.json"
    if progress_file.exists():
        progress_file.unlink()
        
    subprocess.run(cmd)

def main():
    print("="*50)
    print("REVOLUT BATCH INGESTION (STOCKS + CRYPTO)")
    print("="*50)
    
    files = list(SOURCE_DIR.glob("*.pdf"))
    all_transactions = []
    
    for pdf in files:
        name = pdf.name.lower()
        
        # 1. TRADING ACCOUNT (Stocks)
        if "trading-account-statement" in name:
            print(f"> Processing STOCKS: {name}")
            out_name = f"revolut_stocks_{pdf.stem[:10]}.json"
            run_mistral_loop(pdf, out_name)
            
            data = load_json(WORK_DIR / out_name)
            txs = data.get('transactions', [])
            print(f"  Extracted: {len(txs)}")
            all_transactions.extend(txs)
            
        # 2. CRYPTO ACCOUNT
        elif "crypto-account-statement" in name:
            print(f"> Processing CRYPTO: {name}")
            out_name = f"revolut_crypto_{pdf.stem[:10]}.json"
            run_mistral_loop(pdf, out_name)
            
            data = load_json(WORK_DIR / out_name)
            txs = data.get('transactions', [])
            print(f"  Extracted: {len(txs)}")
            all_transactions.extend(txs)
            
    # Save Combined
    full_path = WORK_DIR / "revolut_transactions_full.json"
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump({"transactions": all_transactions}, f, indent=2)
        
    print(f"\nTotal Transactions: {len(all_transactions)}")
    
    # Run Reconciliation (History Only)
    empty_holdings = WORK_DIR / "empty_holdings.json"
    with open(empty_holdings, 'w') as f:
        json.dump({"holdings": []}, f)
        
    print("\nRunning History Builder (No Snapshot)...")
    cmd = [
        str(Path(sys.executable)),
        str(WORK_DIR / "reconciliation_engine.py"),
        "--holdings", str(empty_holdings),
        "--transactions", str(full_path)
    ]
    subprocess.run(cmd)

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

if __name__ == "__main__":
    main()
