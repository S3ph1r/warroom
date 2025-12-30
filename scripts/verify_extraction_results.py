"""
Script to verify extraction using EXISTING cached parsers.
Print sample records to verify data quality.
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.router import DocumentType

def verify_extraction():
    print("="*60)
    print("🔍 VERIFYING CACHED PARSERS")
    print("="*60)
    
    engine = ExtractionEngine(prefer_google=True)
    
    files = [
        (Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Posizioni_19-dic-2025_17_49_12.csv"), DocumentType.HOLDINGS),
        (Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"), DocumentType.TRANSACTIONS)
    ]
    
    for file_path, doc_type in files:
        print(f"\n📂 Processing: {file_path.name}")
        print(f"   Type: {doc_type.value}")
        
        try:
            results = engine.extract(file_path, "BGSAXO", doc_type)
            
            print(f"   ✅ Extracted {len(results)} records")
            
            if results:
                print("\n   📝 Sample Record [0]:")
                for k, v in results[0].items():
                    print(f"      {k}: {v}")
                
                # Check for critical fields
                if doc_type == DocumentType.HOLDINGS:
                    missing_tickers = sum(1 for r in results if not r.get('ticker') or r.get('ticker') == 'N/A')
                    print(f"   ⚠️ Records with missing ticker: {missing_tickers}/{len(results)}")
                
                if doc_type == DocumentType.TRANSACTIONS:
                   missing_tickers = sum(1 for r in results if not r.get('ticker') or r.get('ticker') == 'UNKNOWN')
                   print(f"   ⚠️ Records with missing ticker: {missing_tickers}/{len(results)}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_extraction()
