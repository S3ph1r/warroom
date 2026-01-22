import sys
import os
import shutil
from pathlib import Path
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.smart_extractor import SmartExtractor
from pypdf import PdfReader, PdfWriter

# Config
full_pdf_path = Path("D:/Download/BGSAXO/Transactions_19807401_2024-11-26_2025-12-19.pdf")
temp_pdf_path = project_root / "temp_page_61.pdf"
page_index = 60 # Page 61

print(f"📄 Preparing Single Page PDF for Vision Test ({temp_pdf_path.name})")

# 1. Create Single Page PDF
reader = PdfReader(str(full_pdf_path))
writer = PdfWriter()
writer.add_page(reader.pages[page_index])

with open(temp_pdf_path, "wb") as f:
    writer.write(f)

print("✅ Created temporary single-page PDF.")

# 2. Run Smart Extractor with Forced Vision
extractor = SmartExtractor(project_root / "extraction_results_vision_test.json")

# Mock classification to force Vision
file_info = {
    "broker": "BGSAXO",
    "classification": {
        "extraction_strategy": "VISION_LLM",
        "document_type": "Financial Statement",
        "content_summary": "Transaction History with ISIN details" 
    }
}

print("\n👁️ Running Vision Extraction...")
try:
    rows = extractor._extract_from_pdf(temp_pdf_path, file_info)
    
    print("\n--- Extracted Rows (Vision) ---")
    import json
    print(json.dumps(rows, indent=2))
    
    # 3. Validation
    found_isin = any(r.get("isin") for r in rows)
    if found_isin:
        print("\n✅ SUCCESS: ISIN found in Vision extraction!")
    else:
        print("\n❌ FAILURE: No ISIN found in Vision extraction.")

except Exception as e:
    print(f"\n❌ Error during extraction: {e}")

finally:
    # Cleanup
    if temp_pdf_path.exists():
        os.remove(temp_pdf_path)
        print("\n🧹 Cleanup: Removed temp file.")
