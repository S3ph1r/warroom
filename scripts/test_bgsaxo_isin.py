import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.smart_extractor import SmartExtractor
# from scripts.ingestion_lib import extract_text_pypdf # Not needed, using pypdf directly

pdf_path = Path("D:/Download/BGSAXO/Transactions_19807401_2024-11-26_2025-12-19.pdf")
page_index = 60 # Page 61 (0-indexed)

print(f"📄 Testing extraction on {pdf_path.name} - Page {page_index+1}")

# Extract raw text first to verify content
# full_text = extract_text_pypdf(pdf_path)
# We need just one page. pypdf extractor returns full text or we need a way to get specific page.
# SmartExtractor._extract_from_pdf iterates pages.
# Let's instantiate SmartExtractor and call a protected method or just _extract_from_pdf and limit it?

# Better: Use pypdf directly to get the single page text, then call _extract_from_pdf_text_raw
import pypdf
reader = pypdf.PdfReader(pdf_path)
page_text = reader.pages[page_index].extract_text()

print(f"\n--- Raw Text Snippet (First 500 chars) ---\n{page_text[:500]}...\n------------------------------------------")

extractor = SmartExtractor(project_root / "extraction_results_test.json")
file_info = {"document_type": "Financial Statement"}

# Call the text extraction method
rows = extractor._extract_from_pdf_text_raw(page_text, file_info)

print("\n--- Extracted Rows ---")
import json
print(json.dumps(rows, indent=2))

found_isin = any(r.get("isin") for r in rows)
if found_isin:
    print("\n✅ SUCCESS: ISIN found in extraction!")
else:
    print("\n❌ FAILURE: No ISIN found.")
