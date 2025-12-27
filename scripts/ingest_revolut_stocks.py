
import sys
import json
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)

WORK_DIR = Path(r"D:\Download\Progetto WAR ROOM\warroom\scripts")
SOURCE_DIR = Path(r"D:\Download\Revolut")
TARGET_FILE = "trading-account-statement_2019-12-28_2025-12-26_it-it_e34cc5.pdf"

def main():
    print(f"REVOLUT STOCKS - TARGETING {TARGET_FILE}")
    
    pdf_path = SOURCE_DIR / TARGET_FILE
    if not pdf_path.exists():
        print(f"Error: File not found in {SOURCE_DIR}")
        # Try to match partial name if exact fails?
        candidates = list(SOURCE_DIR.glob("*e34cc5.pdf"))
        if candidates:
            pdf_path = candidates[0]
            print(f"Found match: {pdf_path.name}")
        else:
            return

    output = WORK_DIR / "revolut_stocks_full.json"
    
    # Cleanup progress
    progress_file = WORK_DIR / "progress.json"
    if progress_file.exists():
        progress_file.unlink()
        
    cmd = [
        str(Path(sys.executable)),
        str(WORK_DIR / "extract_all_transactions.py"),
        "--pdf", str(pdf_path),
        "--output", str(output)
    ]
    subprocess.run(cmd)
    
    # Run Reconciliation
    print("\nRunning Reconciliation...")
    empty_holdings = WORK_DIR / "empty_holdings.json"
    if not empty_holdings.exists():
        with open(empty_holdings, 'w') as f:
            json.dump({"holdings": []}, f)
            
    cmd_recon = [
        str(Path(sys.executable)),
        str(WORK_DIR / "reconciliation_engine.py"),
        "--holdings", str(empty_holdings),
        "--transactions", str(output)
    ]
    subprocess.run(cmd_recon)

if __name__ == "__main__":
    main()
