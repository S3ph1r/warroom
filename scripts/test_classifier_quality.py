import sys
from pathlib import Path
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.smart_classifier import full_classify_pdf_text

# Target PDF (Known BGSAXO with bad table extraction)
pdf_path = Path("D:/Download/BGSAXO/Transactions_19807401_2024-11-26_2025-12-19.pdf")

print(f"📄 Testing Text Quality Analysis on {pdf_path.name}")

# 1. Simulate Pre-analysis (Text Extraction)
try:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    # Page 1 usually has no transactions, Page 61 does. 
    # But classifier usually looks at Page 0. 
    # If Page 0 text is okay, it might say HIGH.
    # We should verify if the BGSAXO PDF has bad text EVERYWHERE or just on table pages.
    # Let's extract Page 60 (index 60 = Page 61) to fully simulate the issue.
    # Wait, the classifier `full_classify_pdf_text` is usually called on the *first page* text or aggregated text?
    # In `smart_classifier.py`: `first_page_text = reader.pages[0].extract_text()`
    # Page 0 might be clean. Testing Page 60 (Index 60) where the table is.
    page_text = reader.pages[60].extract_text()
    print(f"\n--- Page 61 Text Preview ---\n{page_text[:300]}...\n---------------------------")
    
    # 2. Call Classifier
    result = full_classify_pdf_text(pdf_path, page_text)
    
    print("\n--- Classification Result ---")
    print(f"Text Quality: {result.get('text_quality')}")
    print(f"Strategy:     {result.get('extraction_strategy')}")
    print(f"Reason:       {result.get('strategy_reason')}")
    
    if result.get("text_quality") == "LOW" and result.get("extraction_strategy") == "VISION_LLM":
        print("\n✅ SUCCESS: Correctly identified garbage text and switched to Vision.")
    else:
        print("\n⚠️ WARNING: Classifier thinks text is HIGH quality.")
        # If Page 1 is clean, we might need to verify Page 61 text quality too??
        # But the classifier standardizes on checking the "document".
        
except Exception as e:
    print(f"❌ Error: {e}")
