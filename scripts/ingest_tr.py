
import sys
import json
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO)

WORK_DIR = Path(r"D:\Download\Progetto WAR ROOM\warroom\scripts")
PDF_PATH = Path(r"D:\Download\Trade Repubblic\Estratto conto.pdf")
OUTPUT_JSON = WORK_DIR / "tr_transactions.json"

def main():
    print("TRADE REPUBLIC INGESTION")
    
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
