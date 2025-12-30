
import sys
from pathlib import Path
import logging

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.pipeline.dynamic_pdf_parser import DynamicPDFParser

# Setup logging
logging.basicConfig(level=logging.INFO)

def main():
    parser = DynamicPDFParser()
    pdf_path = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"
    
    print("--- STARTING DISCOVERY TEST ---")
    schemas = parser.discover_structure(pdf_path)
    
    print("\n--- DISCOVERED SCHEMAS ---")
    import json
    print(json.dumps(schemas, indent=2))

if __name__ == "__main__":
    main()
