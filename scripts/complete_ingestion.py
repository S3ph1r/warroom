"""
COMPLETE DOCUMENT INGESTION SYSTEM
===================================
1. Classifica documento (Holdings / Transazioni / Misto)
2. Etichetta per non rielaborare
3. Estrae holdings E/O transazioni

FLOW:
Document -> Mistral Classification -> Mistral Instructions -> Pandas Extract -> DB
"""
import json
import requests
import pandas as pd
import fitz  # PyMuPDF for PDFs
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral-nemo:latest"

# Document registry to avoid reprocessing
PROCESSED_DOCS = {}

def get_document_preview(file_path: str, max_lines: int = 25) -> tuple[str, str]:
    """Get document preview and detect file type."""
    path = Path(file_path)
    file_type = path.suffix.lower()
    
    if file_type == '.csv':
        with open(path, 'r', encoding='utf-8-sig') as f:
            lines = [f"LINE {i}: {line.strip()[:180]}" for i, line in enumerate(f) if i < max_lines]
        return "\n".join(lines), "csv"
        
    elif file_type == '.pdf':
        try:
            doc = fitz.open(path)
            text = []
            for page_num in range(min(3, len(doc))):  # First 3 pages
                page = doc[page_num]
                page_text = page.get_text("text")[:1500]
                text.append(f"=== PAGE {page_num+1} ===\n{page_text}")
            return "\n".join(text), "pdf"
        except Exception as e:
            return f"Error reading PDF: {e}", "pdf"
    else:
        return f"Unsupported file type: {file_type}", file_type

def classify_document(preview: str, filename: str) -> dict:
    """
    Mistral classifica il documento e dice cosa contiene.
    """
    PROMPT = f"""Analizza questo documento finanziario e classificalo.

FILENAME: {filename}

CONTENUTO:
{preview}

CLASSIFICA il documento:
1. Contiene HOLDINGS (posizioni attuali, portafoglio)? 
2. Contiene TRANSACTIONS (operazioni, compravendite, dividendi)?
3. È un documento MISTO (entrambi)?

Per HOLDINGS cerca: quantità possedute, valore di mercato, posizioni aperte
Per TRANSACTIONS cerca: date operazioni, BUY/SELL, importi, commissioni

Rispondi JSON:
{{
  "document_type": "holdings" | "transactions" | "mixed",
  "contains_holdings": true/false,
  "contains_transactions": true/false,
  "confidence": 0.0-1.0,
  "detected_sections": [
    {{"type": "holdings", "description": "tabella posizioni", "location": "pagina 1"}},
    {{"type": "transactions", "description": "lista operazioni", "location": "pagine 2-5"}}
  ],
  "summary": "breve descrizione del documento"
}}"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 1024}
        },
        timeout=120
    )
    
    if response.status_code == 200:
        try:
            return json.loads(response.json().get("response", "{}"))
        except:
            return {"error": "Failed to parse classification"}
    return {"error": f"API error: {response.status_code}"}

def get_extraction_instructions(preview: str, doc_type: str, extract_type: str) -> dict:
    """
    Mistral genera istruzioni per estrarre holdings O transazioni.
    """
    if extract_type == "holdings":
        PROMPT = f"""Genera istruzioni per estrarre HOLDINGS (posizioni) da questo documento.

DOCUMENTO ({doc_type}):
{preview}

Fornisci istruzioni JSON per pandas:
{{
  "extraction_type": "holdings",
  "file_type": "{doc_type}",
  "instructions": {{
    "header_row": 0,
    "skip_rows": [],
    "data_start_row": 1
  }},
  "column_names": {{
    "name": "nome colonna asset",
    "ticker": "nome colonna ticker",
    "isin": "nome colonna ISIN",
    "quantity": "nome colonna quantità",
    "purchase_price": "nome colonna prezzo acquisto",
    "currency": "nome colonna valuta"
  }},
  "validation": {{
    "expected_count": 0,
    "first_asset": "nome primo asset"
  }}
}}"""
    else:  # transactions
        PROMPT = f"""Genera istruzioni per estrarre TRANSACTIONS (operazioni) da questo documento.

DOCUMENTO ({doc_type}):
{preview}

Per le transazioni cerca:
- Data operazione
- Tipo (BUY/SELL/DIVIDEND/FEE)
- Asset/Ticker
- Quantità
- Prezzo
- Importo totale
- Commissioni

Fornisci istruzioni JSON:
{{
  "extraction_type": "transactions",
  "file_type": "{doc_type}",
  "instructions": {{
    "header_row": 0,
    "skip_rows": [],
    "data_start_row": 1
  }},
  "column_names": {{
    "date": "nome colonna data",
    "type": "nome colonna tipo operazione",
    "asset": "nome colonna asset/ticker",
    "quantity": "nome colonna quantità",
    "price": "nome colonna prezzo",
    "amount": "nome colonna importo",
    "fees": "nome colonna commissioni",
    "currency": "nome colonna valuta"
  }},
  "transaction_type_mapping": {{
    "Acquisto": "BUY",
    "Vendita": "SELL",
    "Dividendo": "DIVIDEND"
  }},
  "validation": {{
    "expected_count": 0,
    "sample_transaction": {{}}
  }}
}}"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 2048}
        },
        timeout=180
    )
    
    if response.status_code == 200:
        try:
            return json.loads(response.json().get("response", "{}"))
        except:
            return {"error": "Failed to parse instructions"}
    return {"error": f"API error: {response.status_code}"}

def process_document_complete(file_path: str):
    """
    Complete processing: classify, label, extract all relevant data.
    """
    path = Path(file_path)
    filename = path.name
    
    print("="*70)
    print("COMPLETE DOCUMENT INGESTION")
    print("="*70)
    print(f"File: {filename}")
    print()
    
    # Check if already processed
    if filename in PROCESSED_DOCS:
        print(f"Already processed! Label: {PROCESSED_DOCS[filename]}")
        return PROCESSED_DOCS[filename]
    
    # Step 1: Get preview
    print("STEP 1: Reading document...")
    preview, file_type = get_document_preview(file_path)
    print(f"Type: {file_type}, Preview length: {len(preview)} chars")
    print()
    
    # Step 2: Classify
    print("STEP 2: Classifying document with Mistral...")
    classification = classify_document(preview, filename)
    print(json.dumps(classification, indent=2, ensure_ascii=False))
    print()
    
    doc_type = classification.get("document_type", "unknown")
    
    # Label document
    PROCESSED_DOCS[filename] = {
        "file": str(file_path),
        "type": doc_type,
        "classification": classification,
        "processed_at": datetime.now().isoformat(),
        "extractions": {}
    }
    
    # Step 3: Extract based on type
    results = {"holdings": [], "transactions": []}
    
    if doc_type in ["holdings", "mixed"]:
        print("STEP 3a: Extracting HOLDINGS...")
        instructions = get_extraction_instructions(preview, file_type, "holdings")
        if "column_names" in instructions:
            # Here we would call pandas extraction
            print(f"  Instructions: {json.dumps(instructions.get('column_names', {}), ensure_ascii=False)}")
            PROCESSED_DOCS[filename]["extractions"]["holdings"] = instructions
    
    if doc_type in ["transactions", "mixed"]:
        print("STEP 3b: Extracting TRANSACTIONS...")
        instructions = get_extraction_instructions(preview, file_type, "transactions")
        if "column_names" in instructions:
            print(f"  Instructions: {json.dumps(instructions.get('column_names', {}), ensure_ascii=False)}")
            PROCESSED_DOCS[filename]["extractions"]["transactions"] = instructions
    
    # Save registry
    with open("scripts/document_registry.json", "w", encoding="utf-8") as f:
        json.dump(PROCESSED_DOCS, f, indent=2, ensure_ascii=False)
    
    print()
    print("="*70)
    print(f"DOCUMENT LABELED: {doc_type}")
    print(f"Saved to: scripts/document_registry.json")
    print("="*70)
    
    return PROCESSED_DOCS[filename]

if __name__ == "__main__":
    # Test with BG SAXO files
    files = [
        r"D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv",
        r"D:\Download\BGSAXO\Transactions_19807401_2025-01-01_2025-12-19.pdf"
    ]
    
    for f in files:
        if Path(f).exists():
            result = process_document_complete(f)
            print()
