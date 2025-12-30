"""
Hybrid PDF Parser for Financial Transactions (BG SAXO Optimized)
Strategy:
1. Python: Smart Chunking (Group lines by Date/Transaction)
2. Ollama: Micro-extraction of details from chunks
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import requests
import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Ollama config
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
OLLAMA_URL = "http://localhost:11434/api/chat"

class TransactionBlock:
    def __init__(self, date_str: str, main_line: str):
        self.date = date_str
        self.main_line = main_line
        self.details: List[str] = []
    
    def add_detail(self, line: str):
        self.details.append(line)
    
    def full_text(self) -> str:
        return f"{self.main_line}\n" + "\n".join(self.details)

def parse_pdf_structure(file_path: str) -> List[TransactionBlock]:
    """
    Step 1: Read PDF and chunk into logic blocks (Transaction + its details)
    """
    logger.info(f"   Reading PDF structure: {Path(file_path).name}")
    blocks = []
    current_date = None
    current_block = None
    
    # Regex identifiers
    # Dates: "19-dic-2025" or "26-nov-2024"
    date_pattern = re.compile(r'^\d{1,2}-[a-z]{3}-\d{4}$', re.IGNORECASE)
    
    # Start of transaction: "Contrattazione", "Operazionesulcapitale", "Op. sul capitale"
    start_keywords = ["Contrattazione", "Operazione", "Op. sul capitale"]
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check Date Header
                if date_pattern.match(line):
                    current_date = line
                    continue
                
                # Check New Transaction Start
                is_new_start = any(line.startswith(kw) for kw in start_keywords)
                
                if is_new_start and current_date:
                    # Save previous block
                    if current_block:
                        blocks.append(current_block)
                    
                    # Start new block
                    current_block = TransactionBlock(current_date, line)
                
                elif current_block:
                    # Append strictly related details (Fees, Id, ISIN)
                    # Skip page headers/footers if detected (simple length check or keyword)
                    if "Pagina" not in line and "Trascinato" not in line:
                         current_block.add_detail(line)
    
    # Append last block
    if current_block:
        blocks.append(current_block)
        
    logger.info(f"   Found {len(blocks)} transaction blocks")
    return blocks

def extract_details_with_ollama(blocks: List[TransactionBlock], batch_size: int = 5) -> List[Dict]:
    """
    Step 2: Send blocks to Ollama for detail extraction
    """
    transactions = []
    logger.info(f"   Extracting details with Ollama ({OLLAMA_MODEL})...")
    
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i+batch_size]
        
        # Prepare Batch Prompt
        prompt_text = "Estrai i dati delle seguenti transazioni in formato JSON. \n"
        prompt_text += "Output atteso: Lista di oggetti con keys: ticker, operation (BUY/SELL/DIVIDEND), quantity (float), price (float), currency (str), fees (float), total_amount (float), isin (str).\n\n"
        
        for idx, block in enumerate(batch):
            prompt_text += f"--- TRANSAZIONE {idx} (Data: {block.date}) ---\n"
            prompt_text += f"{block.full_text()}\n\n"
            
        prompt_text += "Restituisci SOLO il JSON valido (lista di oggetti)."
        
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt_text}],
                "stream": False,
                "format": "json" # Force JSON mode if supported
            }, timeout=120)
            
            if response.status_code == 200:
                content = response.json().get('message', {}).get('content', '')
                
                # Try to parse JSON
                try:
                    data = json.loads(content)
                    
                    # Handle if LLM returned dict instead of list
                    if isinstance(data, dict):
                        # Some models wrap in {"transactions": [...]}
                        data = data.get('transactions', data.get('items', [data]))
                    
                    if isinstance(data, list):
                        # Merge Date from blocks
                        for j, item in enumerate(data):
                            if j < len(batch):
                                item['date'] = batch[j].date
                                transactions.append(item)
                    else:
                        logger.warning(f"   Ollama returned non-list format: {type(data)}")
                        
                except json.JSONDecodeError:
                    logger.error(f"   Failed to decode JSON from Ollama")
                    logger.debug(f"   Content: {content[:100]}...")
            else:
                 logger.error(f"   Ollama error: {response.status_code}")

        except Exception as e:
            logger.error(f"   Ollama exception: {e}")
            
        if (i+1) % 10 == 0:
            logger.info(f"   Processed {len(transactions)}/{len(blocks)}...")

    return transactions

def parse_transactions_hybrid(file_path: str) -> List[Dict]:
    """
    Main entry point for Hybrid PDF Parsing
    """
    # 1. Chunking
    blocks = parse_pdf_structure(file_path)
    
    if not blocks:
        return []

    # 2. LLM Extraction
    raw_data = extract_details_with_ollama(blocks)
    
    # 3. Standardization (optional: ensure fields map to DB schema)
    final_data = []
    for item in raw_data:
        # Basic cleanup
        if 'operation' in item:
            op = str(item['operation']).upper()
            if 'ACQUISTA' in op or 'BUY' in op: item['operation'] = 'BUY'
            elif 'VENDI' in op or 'SELL' in op: item['operation'] = 'SELL'
        
        final_data.append(item)
        
    return final_data

if __name__ == "__main__":
    # Test
    f = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"
    res = parse_transactions_hybrid(f)
    print(f"Extracted {len(res)} transactions")
    if res:
        print(res[0])
