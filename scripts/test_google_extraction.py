"""
Script to test extraction using Google AI based engine.
Print sample records to verify data quality.
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.router import DocumentType
from ingestion.pipeline.parser_registry import ParserRegistry

def test_extraction():
    print("="*60)
    print("🧪 TESTING GOOGLE AI EXTRACTION ENGINE")
    print("="*60)
    
    # Clear registry to force new generation
    print("🧹 Clearing parser registry...")
    registry = ParserRegistry()
    registry.save("BGSAXO", "HOLDINGS", "dummy", "code") # create dir if needed
    for f in Path("ingestion/generated_parsers").glob("*.json"):
        if f.name == "registry.json":
            f.unlink()
            print("   Registry deleted.")
    
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

    print("\n" + "="*60)
    print("📊 ENGINE STATS")
    print(engine.get_stats())
    print("="*60)

if __name__ == "__main__":
    test_extraction()
