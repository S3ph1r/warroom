"""
Mistral Document Analyzer - One File at a Time
===============================================
Passes each document to Mistral for analysis and extraction.
Processes ONE file at a time and shows results for user review.
"""
import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")
OUTPUT_FOLDER = PROJECT_ROOT / 'data' / 'extracted'
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Prompt template
PROMPT_TEMPLATE = """You are a financial document analyzer for the broker: {broker_name}.

ANALYZE THIS DOCUMENT AND EXTRACT DATA.

## STEP 1 - DOCUMENT IDENTIFICATION
Determine:
1. FORMAT: The file extension (CSV, XLSX, PDF)
2. CONTENT_TYPE: Choose one:
   - "HOLDINGS" = Current portfolio positions (what the investor owns NOW)
   - "TRANSACTIONS" = Historical buy/sell operations
   - "OTHER" = Reports, summaries, or unrelated documents
3. DOCUMENT_DATE: The date this snapshot refers to (format: YYYY-MM-DD)

## STEP 2 - DATA EXTRACTION (only if HOLDINGS)
Extract a table with these REQUIRED fields:
- ticker: Asset symbol (e.g., "NVDA", "AAPL", "BTC")
- isin: ISIN code (e.g., "US67066G1040") or null if not present
- quantity: Number of shares/units owned (positive number)
- currency: Native currency of the asset (e.g., "USD", "EUR", "GBP")

OPTIONAL fields (include if available):
- name: Full asset name
- purchase_price: Average acquisition cost per unit
- current_value: Total current market value

## OUTPUT FORMAT
Return ONLY valid JSON, no markdown, no explanation:

{{
  "document_format": "CSV",
  "content_type": "HOLDINGS",
  "document_date": "2025-12-19",
  "broker": "{broker_name}",
  "data": [
    {{"ticker": "NVDA", "isin": "US67066G1040", "quantity": 10.0, "currency": "USD"}},
    {{"ticker": "AAPL", "isin": "US0378331005", "quantity": 5.0, "currency": "USD"}}
  ],
  "total_records": 2,
  "confidence": 0.95,
  "notes": "Any issues or observations about the extraction"
}}

If CONTENT_TYPE is "TRANSACTIONS" or "OTHER", return minimal JSON:
{{
  "document_format": "PDF",
  "content_type": "TRANSACTIONS",
  "document_date": "2025-12-19",
  "broker": "{broker_name}",
  "data": [],
  "total_records": 0,
  "confidence": 0.90,
  "notes": "This document contains transaction history, not current holdings"
}}

---
DOCUMENT CONTENT (filename: {filename}):

{file_content}
"""


def read_file_content(filepath: Path, max_chars: int = 50000) -> str:
    """Read file content based on type."""
    ext = filepath.suffix.lower()
    
    if ext == '.csv':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    elif ext in ['.xlsx', '.xls']:
        try:
            import pandas as pd
            df = pd.read_excel(filepath)
            content = df.to_csv(index=False)
        except Exception as e:
            content = f"[Error reading Excel: {e}]"
    elif ext == '.pdf':
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            content = ""
            for page in doc:
                content += page.get_text()
            doc.close()
        except Exception as e:
            content = f"[Error reading PDF: {e}]"
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    
    # Truncate if too long
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[TRUNCATED - showing first {max_chars} chars]"
    
    return content


def call_mistral(prompt: str) -> str:
    """Call Ollama/Mistral API."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for structured output
                    "num_predict": 8000,  # Allow long response for many holdings
                }
            },
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            return f"[API Error: {response.status_code}]"
            
    except Exception as e:
        return f"[Connection Error: {e}]"


def parse_json_response(response: str) -> dict:
    """Extract JSON from Mistral response."""
    import re
    
    # Try to find JSON in the response
    # Remove markdown code blocks if present
    response = re.sub(r'```json\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    
    # Find JSON object
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse error: {e}", "raw_response": response[:500]}
    
    return {"error": "No JSON found in response", "raw_response": response[:500]}


def process_single_file(filepath: Path, broker_name: str) -> dict:
    """Process a single file through Mistral."""
    print(f"\n{'='*60}")
    print(f"PROCESSING: {filepath.name}")
    print(f"{'='*60}")
    
    # Read content
    print("Reading file content...")
    content = read_file_content(filepath)
    print(f"Content length: {len(content)} chars")
    
    # Build prompt
    prompt = PROMPT_TEMPLATE.format(
        broker_name=broker_name,
        filename=filepath.name,
        file_content=content
    )
    
    # Call Mistral
    print(f"\nCalling Mistral ({OLLAMA_MODEL})...")
    print("This may take a minute...")
    
    raw_response = call_mistral(prompt)
    
    # Parse response
    result = parse_json_response(raw_response)
    
    # Add metadata
    result['source_file'] = filepath.name
    result['processed_at'] = datetime.now().isoformat()
    
    return result


def main():
    """Main function - process first BG SAXO file."""
    
    BROKER_NAME = "BG_SAXO"
    BROKER_FOLDER = Path(r'G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo')
    
    # List all files
    files = sorted(BROKER_FOLDER.glob('*'))
    
    print(f"\n📂 Files in {BROKER_FOLDER}:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name} ({f.suffix})")
    
    if not files:
        print("❌ No files found!")
        return

    print(f"\n🎯 Processing FIRST file: {files[0].name}")
    
    # Process first file
    result = process_single_file(files[0], BROKER_NAME)
    
    # Display result
    print("\n" + "="*60)
    print("MISTRAL RESPONSE:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Save result
    if 'content_type' in result:
        content_type = result.get('content_type', 'unknown').lower()
        doc_date = result.get('document_date', datetime.now().strftime('%Y-%m-%d'))
        doc_format = result.get('document_format', 'unknown').lower()
        
        output_name = f"{BROKER_NAME}-{content_type}-{doc_date}.{doc_format}.json"
    else:
        output_name = f"{BROKER_NAME}-{files[0].stem}.json"
    
    output_path = OUTPUT_FOLDER / output_name
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {output_path}")
    
    # Summary
    if 'data' in result and result['data']:
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"   Content Type: {result.get('content_type', 'N/A')}")
        print(f"   Document Date: {result.get('document_date', 'N/A')}")
        print(f"   Total Records: {result.get('total_records', len(result['data']))}")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
        
        print(f"\n📋 First 5 records:")
        for h in result['data'][:5]:
            ticker = h.get('ticker', '?')
            isin = h.get('isin', 'N/A')
            qty = h.get('quantity', 0)
            curr = h.get('currency', '?')
            print(f"   {ticker:12} | {isin:14} | {qty:>10} | {curr}")


if __name__ == "__main__":
    main()
