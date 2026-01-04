"""
Test Income Statement Extraction
Test if the parser can extract transactions from Income statement files.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ingest_scalable_v2 import extract_transactions_from_income_statement

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")
TARGET = "20250506 Income statement Baader Bank pV94w5.pdf"

def test_income():
    pdf_path = INBOX / TARGET
    
    print(f"Testing: {pdf_path.name}")
    print("=" * 60)
    
    txs = extract_transactions_from_income_statement(pdf_path)
    
    print(f"\n✅ Extracted {len(txs)} transactions:")
    for tx in txs:
        print(f"  - {tx.timestamp.date()} | {tx.operation} | {tx.ticker} | Qty: {tx.quantity}")
        
    if len(txs) == 0:
        print("\n❌ NO TRANSACTIONS EXTRACTED!")
        print("   Income statement format may be incompatible with current parser.")

if __name__ == "__main__":
    test_income()
