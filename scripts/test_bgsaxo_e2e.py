"""
E2E Test: BG Saxo Ingestion Pipeline
=====================================
Tests both Holdings (CSV) and Transactions (PDF) extraction and DB storage.
Uses the new Hybrid CSV Parser and Block-Based PDF Parser.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.router import DocumentType
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# BG Saxo files
BGSAXO_HOLDINGS = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv"
BGSAXO_TRANSACTIONS = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"

def test_extraction():
    """Test extraction without DB insertion"""
    engine = ExtractionEngine()
    
    print("\n" + "="*60)
    print("TEST 1: Holdings CSV Extraction")
    print("="*60)
    
    holdings = engine.extract(
        file_path=Path(BGSAXO_HOLDINGS),
        broker="BG_SAXO",
        doc_type=DocumentType.HOLDINGS
    )
    
    print(f"\n📊 Holdings extracted: {len(holdings)}")
    if holdings:
        print("Sample record:")
        sample = holdings[0]
        for k, v in list(sample.items())[:6]:
            print(f"  {k}: {v}")
    
    print("\n" + "="*60)
    print("TEST 2: Transactions PDF Extraction")
    print("="*60)
    
    transactions = engine.extract(
        file_path=Path(BGSAXO_TRANSACTIONS),
        broker="BG_SAXO",
        doc_type=DocumentType.TRANSACTIONS
    )
    
    print(f"\n📊 Transactions extracted: {len(transactions)}")
    if transactions:
        # Show sample with ISIN
        sample_with_isin = next((t for t in transactions if t.get('isin')), transactions[0])
        print("Sample record (with ISIN):")
        for k, v in list(sample_with_isin.items())[:8]:
            print(f"  {k}: {v}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Holdings:     {len(holdings)} records")
    print(f"Transactions: {len(transactions)} records")
    
    # Count records with ISIN
    with_isin = sum(1 for t in transactions if t.get('isin'))
    print(f"Transactions with ISIN: {with_isin}/{len(transactions)} ({100*with_isin//len(transactions) if transactions else 0}%)")
    
    return holdings, transactions

if __name__ == "__main__":
    test_extraction()
