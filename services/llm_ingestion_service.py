"""
LLM Ingestion Service
=====================
Uses local Mistral (via Ollama) to parse broker documents and extract
structured data for Holdings and Transactions.
"""
import os
import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests
import uuid

import fitz  # PyMuPDF
import pandas as pd
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import IngestionBatch

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")

# Output directory for extracted JSONs
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "extracted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PROMPT TEMPLATES
# ============================================================

PROMPT_HOLDINGS = """You are a financial document parser. Extract current portfolio holdings from this document.

RULES:
- Only extract ACTUAL holdings (not headers, totals, or empty rows)
- Normalize ticker symbols (remove exchange suffixes like ":xnys")
- If ISIN is available, include it
- purchase_price = average acquisition cost (NOT current market price)
- If purchase_price is unavailable, set to null
- currency = the native currency of the asset
- quantity must be a positive number

Return ONLY valid JSON (no markdown, no explanation):
{{
  "broker": "{broker}",
  "document_type": "holdings",
  "extraction_date": "{date}",
  "holdings": [
    {{
      "ticker": "ORCL",
      "isin": "US68389X1054",
      "name": "Oracle Corporation",
      "quantity": 3.0,
      "purchase_price": 222.53,
      "current_value": 502.50,
      "currency": "USD"
    }}
  ],
  "cash_positions": [
    {{"currency": "EUR", "amount": 133.10}}
  ],
  "confidence": 0.95,
  "notes": "Any relevant notes"
}}

---
DOCUMENT CONTENT:
{content}
"""

PROMPT_TRANSACTIONS = """You are a financial document parser. Extract all transactions from this document.

TRANSACTION TYPES (use exactly these):
- BUY = Purchase of asset
- SELL = Sale of asset
- DIVIDEND = Dividend payment received
- DEPOSIT = Cash deposit
- WITHDRAW = Cash withdrawal
- FEE = Commission or fee charged
- TRANSFER_IN = Asset transferred in
- TRANSFER_OUT = Asset transferred out

RULES:
- Date format: YYYY-MM-DD
- All amounts should be positive (type indicates direction)
- Include fees if mentioned separately

Return ONLY valid JSON (no markdown, no explanation):
{{
  "broker": "{broker}",
  "document_type": "transactions",
  "period": {{"from": "2025-01-01", "to": "2025-12-19"}},
  "transactions": [
    {{
      "date": "2025-03-15",
      "type": "BUY",
      "ticker": "NVDA",
      "isin": "US67066G1040",
      "quantity": 2.0,
      "price_per_unit": 187.77,
      "total_amount": 375.54,
      "currency": "USD",
      "fees": 1.00
    }}
  ],
  "confidence": 0.90,
  "notes": "Any relevant notes"
}}

---
DOCUMENT CONTENT:
{content}
"""

PROMPT_MIXED = """You are a financial document parser. This document may contain BOTH holdings AND transactions.

Analyze the document and extract:
1. HOLDINGS: Current positions (if present)
2. TRANSACTIONS: Historical operations (if present)

Return ONLY valid JSON (no markdown, no explanation):
{{
  "broker": "{broker}",
  "document_type": "mixed",
  "extraction_date": "{date}",
  "holdings": [
    {{
      "ticker": "AAPL",
      "isin": "US0378331005",
      "name": "Apple Inc",
      "quantity": 10.0,
      "purchase_price": null,
      "current_value": 1800.00,
      "currency": "USD"
    }}
  ],
  "transactions": [
    {{
      "date": "2025-03-15",
      "type": "BUY",
      "ticker": "AAPL",
      "quantity": 5.0,
      "price_per_unit": 175.00,
      "total_amount": 875.00,
      "currency": "USD",
      "fees": 0
    }}
  ],
  "cash_positions": [],
  "confidence": 0.85,
  "notes": "Any relevant notes"
}}

---
DOCUMENT CONTENT:
{content}
"""


# ============================================================
# TEXT EXTRACTION
# ============================================================


def extract_content_smart(file_path: Path) -> str:
    """
    Extracts content from file, using table detection for PDFs and markdown formatting for CSVs.
    Returns a string optimized for LLM consumption.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    
    if suffix == '.pdf':
        return extract_smart_pdf(file_path)
    elif suffix in ['.csv', '.xls', '.xlsx']:
        return extract_smart_tabular(file_path)
    else:
        return extract_text(file_path)


def extract_smart_pdf(pdf_path: Path) -> str:
    """Extracts PDF content, prioritizing tables converted to Markdown."""
    try:
        doc = fitz.open(pdf_path)
        full_text = []

        for page_num, page in enumerate(doc):
            # 1. Try to find tables
            tabs = page.find_tables()
            if tabs.tables:
                full_text.append(f"--- PAGE {page_num+1} TABLES ---")
                for tab in tabs:
                    # Convert to markdown
                    md = tab.to_markdown()
                    full_text.append(md)
            else:
                # 2. Fallback to text blocks if no tables
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (b[1], b[0])) # Sort by Y, then X
                page_text = "\n".join([b[4] for b in blocks])
                full_text.append(f"--- PAGE {page_num+1} TEXT ---")
                full_text.append(page_text)
                
        return "\n\n".join(full_text)
    except Exception as e:
        logger.error(f"Smart PDF extraction failed for {pdf_path}: {e}")
        return extract_text(pdf_path) # Fallback to basic


def extract_smart_tabular(file_path: Path) -> str:
    """Converts CSV/Excel to Markdown Table string."""
    try:
        if file_path.suffix == '.csv':
            # Auto-detect separator
            try:
                df = pd.read_csv(file_path, sep=None, engine='python')
            except:
                df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
            
        # Clean data
        df = df.where(pd.notnull(df), "")
        
        # Limit rows to 100 for safety (unless highly relevant)
        # But for ingestion we want ALL rows. Mistral context is large.
        # We'll rely on truncation in process_document if it's too big.
        return df.to_markdown(index=False)
    except Exception as e:
        logger.error(f"Smart Tabular extraction failed for {file_path}: {e}")
        return ""


def extract_text(file_path: Path) -> str:
    """Legacy/Fallback extraction."""
    suffix = file_path.suffix.lower()
    try:
        if suffix == '.pdf':
            doc = fitz.open(file_path)
            return "\n".join([p.get_text() for p in doc])
        elif suffix == '.csv':
            return pd.read_csv(file_path).to_string(index=False)
        elif suffix in ['.xlsx', '.xls']:
            return pd.read_excel(file_path).to_string(index=False)
    except Exception:
        pass
    return ""


# ============================================================
# OLLAMA INTEGRATION
# ============================================================

def call_ollama(prompt: str, model: str = None) -> Optional[str]:
    """Call Ollama API with prompt and return response."""
    model = model or OLLAMA_MODEL
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent parsing
                    "num_predict": 4096  # Allow long responses
                }
            },
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            logger.error(f"Ollama error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama. Is it running? (ollama serve)")
        return None
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None


def parse_json_response(response: str) -> Optional[dict]:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    if not response:
        return None
    
    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in response
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.error(f"Failed to parse JSON from response: {response[:200]}...")
    return None


# ============================================================
# MAIN INGESTION FUNCTIONS
# ============================================================

def detect_document_type(file_path: Path, text_preview: str) -> str:
    """Detect document type based on filename and content."""
    name_lower = file_path.name.lower()
    
    # Check filename patterns
    if any(x in name_lower for x in ['posizioni', 'holdings', 'financial status', 'portfolio']):
        return 'holdings'
    if any(x in name_lower for x in ['transactions', 'trades', 'transazioni', 'estratto conto']):
        return 'transactions'
    if any(x in name_lower for x in ['account-statement', 'rendiconto']):
        return 'mixed'
    
    # Check content patterns
    text_lower = text_preview[:2000].lower()
    has_holdings = any(x in text_lower for x in ['quantity', 'quantità', 'shares', 'units'])
    has_transactions = any(x in text_lower for x in ['buy', 'sell', 'acquisto', 'vendita', 'date'])
    
    if has_holdings and has_transactions:
        return 'mixed'
    elif has_holdings:
        return 'holdings'
    elif has_transactions:
        return 'transactions'
    
    return 'mixed'  # Default to mixed for safety


def detect_broker(file_path: Path) -> str:
    """Detect broker from file path."""
    path_str = str(file_path).upper()
    
    if 'BGSAXO' in path_str or 'BG_SAXO' in path_str:
        return 'BG_SAXO'
    if 'SCALABLE' in path_str:
        return 'SCALABLE'
    if 'TRADE' in path_str and 'REPUBLIC' in path_str:
        return 'TRADE_REPUBLIC'
    if 'REVOLUT' in path_str:
        return 'REVOLUT'
    if 'IBKR' in path_str:
        return 'IBKR'
    if 'BINANCE' in path_str:
        return 'BINANCE'
    
    return 'UNKNOWN'


def process_document(file_path: Path, doc_type: str = None, broker: str = None) -> Optional[dict]:
    """
    Process a single document through LLM extraction.
    
    Args:
        file_path: Path to the document
        doc_type: 'holdings', 'transactions', or 'mixed' (auto-detect if None)
        broker: Broker name (auto-detect if None)
    
    Returns:
        Extracted data as dict, or None on failure
    """
    logger.info(f"Processing: {file_path.name}")
    
    # Extract Text (Smart)
    text = extract_content_smart(file_path)
    if not text:
        logger.error(f"No text extracted from {file_path}")
        return None
    
    # Truncate if too long (Mistral context limit)
    max_chars = 25000  # Leave room for prompt
    if len(text) > max_chars:
        logger.warning(f"Truncating text from {len(text)} to {max_chars} chars")
        text = text[:max_chars]
    
    # Auto-detect type and broker
    doc_type = doc_type or detect_document_type(file_path, text)
    broker = broker or detect_broker(file_path)
    today = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"  Type: {doc_type}, Broker: {broker}")
    
    # Select prompt template
    if doc_type == 'holdings':
        prompt = PROMPT_HOLDINGS.format(broker=broker, date=today, content=text)
    elif doc_type == 'transactions':
        prompt = PROMPT_TRANSACTIONS.format(broker=broker, content=text)
    else:
        prompt = PROMPT_MIXED.format(broker=broker, date=today, content=text)
    
    # Call Ollama
    logger.info("  Calling Mistral...")
    response = call_ollama(prompt)
    
    if not response:
        logger.error("  No response from Ollama")
        return None
    
    # Parse JSON
    result = parse_json_response(response)
    
    if result:
        result['_source_file'] = str(file_path)
        result['_processed_at'] = datetime.now().isoformat()
        logger.info(f"  ✓ Extracted: {len(result.get('holdings', []))} holdings, {len(result.get('transactions', []))} transactions")
        
        # Save to DB
        try:
            save_to_database(result, file_path, broker, doc_type)
        except Exception as e:
            logger.error(f"  Failed to save to DB: {e}")
            
    else:
        logger.error("  ✗ Failed to parse response")
    
    return result


def save_to_database(result: dict, file_path: Path, broker: str, doc_type: str):
    """Save extraction result to IngestionBatch table."""
    session = SessionLocal()
    try:
        # Check if file already ingested (optional: or overwrite)
        # For now, we just append a new batch
        
        batch = IngestionBatch(
            id=uuid.uuid4(),
            broker=broker,
            source_file=str(file_path.name),
            status='PENDING',
            raw_data=result,
            notes=f"DocType: {doc_type}"
        )
        session.add(batch)
        session.commit()
        logger.info(f"  Saved to DB: IngestionBatch {batch.id}")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_extraction(result: dict, output_name: str = None) -> Path:
    """Save extraction result to JSON file."""
    if not output_name:
        source = Path(result.get('_source_file', 'unknown'))
        output_name = f"{source.stem}_{datetime.now().strftime('%H%M%S')}.json"
    
    output_path = OUTPUT_DIR / output_name
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"  Saved to: {output_path.name}")
    return output_path


# ============================================================
# BATCH PROCESSING
# ============================================================

# Broker source folders
BROKER_FOLDERS = {
    'BG_SAXO': Path(r'D:\Download\BGSAXO'),
    'SCALABLE': Path(r'D:\Download\SCALABLE CAPITAL'),
    'TRADE_REPUBLIC': Path(r'D:\Download\Trade Repubblic'),
    'REVOLUT': Path(r'D:\Download\Revolut'),
    'IBKR': Path(r'D:\Download\IBKR'),
    'BINANCE': Path(r'D:\Download\Binance'),
}

# Files to prioritize per broker (most relevant for current holdings/transactions)
PRIORITY_FILES = {
    'BG_SAXO': [
        'Posizioni_19-dic-2025_17_49_12.csv',  # Latest holdings
        'Transactions_19807401_2025-01-01_2025-12-19.pdf',  # 2025 transactions
    ],
    'SCALABLE': [
        '20251219 Financial status Scalable Capital.pdf',  # Latest holdings
    ],
    'TRADE_REPUBLIC': [
        'Estratto conto.pdf',  # Account statement (mixed)
    ],
    'REVOLUT': [
        'account-statement_2020-01-01_2025-12-19_it-it_a1ebdb.pdf',  # Main account
        'crypto-account-statement_2022-07-04_2025-12-20_it-it_1c330c.pdf',  # Crypto
        'trading-account-statement_2019-12-28_2025-12-20_it-it_a927d3.pdf',  # Trading
    ],
    'IBKR': [
        'Rendiconto di attività.pdf',  # Activity statement
        'U22156212.TRANSACTIONS.1Y.csv',  # Transactions CSV
    ],
    'BINANCE': [
        'AccountStatementPeriod_10773818_20251216-20251217_d9522f326b11499f84f5e85f77195e60.pdf',
    ],
}


def get_documents_to_process(broker: str = None) -> list[tuple[str, Path]]:
    """Get list of (broker, file_path) tuples for processing."""
    docs = []
    
    brokers = [broker] if broker else PRIORITY_FILES.keys()
    
    for b in brokers:
        folder = BROKER_FOLDERS.get(b)
        if not folder or not folder.exists():
            continue
        
        for filename in PRIORITY_FILES.get(b, []):
            file_path = folder / filename
            if file_path.exists():
                docs.append((b, file_path))
            else:
                logger.warning(f"File not found: {file_path}")
    
    return docs


def process_all_documents(broker: str = None) -> list[dict]:
    """
    Process all priority documents for ingestion.
    
    Args:
        broker: Process only this broker (None = all brokers)
    
    Returns:
        List of extraction results
    """
    docs = get_documents_to_process(broker)
    
    print("=" * 60)
    print(f"STARTING DOCUMENT INGESTION")
    print(f"Documents to process: {len(docs)}")
    print("=" * 60)
    
    results = []
    
    for i, (broker_name, file_path) in enumerate(docs, 1):
        print(f"\n[{i}/{len(docs)}] {broker_name}: {file_path.name}")
        
        result = process_document(file_path, broker=broker_name)
        
        if result:
            save_extraction(result)
            results.append(result)
        else:
            print(f"  ✗ FAILED")
    
    print("\n" + "=" * 60)
    print(f"COMPLETED: {len(results)}/{len(docs)} documents processed")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    return results


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    if len(sys.argv) > 1:
        # Process specific file
        file_path = Path(sys.argv[1])
        if file_path.exists():
            result = process_document(file_path)
            if result:
                save_extraction(result)
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"File not found: {file_path}")
    else:
        # Process all priority documents
        process_all_documents()
