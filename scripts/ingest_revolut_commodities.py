
import sys
import json
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)

WORK_DIR = Path(r"D:\Download\Progetto WAR ROOM\warroom\scripts")
# Target the Cash file which has XAU/XAG sections
PDF_PATH = Path(r"D:\Download\Revolut\account-statement_2017-12-26_2025-12-26_it-it_3726b9.pdf")
OUTPUT_JSON = WORK_DIR / "revolut_commodities.json"

def main():
    print("REVOLUT COMMODITIES INGESTION")
    
    if not PDF_PATH.exists():
        print("Error: PDF not found")
        return
        
    # Cleanup progress
    progress_file = WORK_DIR / "progress.json"
    if progress_file.exists():
        progress_file.unlink()
        
    cmd = [
        str(Path(sys.executable)),
        str(WORK_DIR / "extract_all_transactions.py"),
        "--pdf", str(PDF_PATH),
        "--output", str(OUTPUT_JSON)
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
