"""
Dynamic PDF Parser for Financial IDP
Strategy: "Omni-Parser" (Multi-Schema & Compressed Format Support)
1. Blind Analyst (LLM): Discovers multiple schemas (Trading, Dividends, Transfers).
2. Miner (Pure Python): Executes schema-specific extraction rules.
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
import requests
import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Ollama config
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
OLLAMA_URL = "http://localhost:11434/api/chat"

class DynamicPDFParser:
    def __init__(self):
        self.schemas = []

    def _call_ollama(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            if json_mode:
                payload["format"] = "json"
                
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get('message', {}).get('content', '')
            return None
        except Exception as e:
            logger.error(f"Ollama exception: {e}")
            return None

    def discover_structure(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Phase 1: Omni-Surveyor
        """
        logger.info(f"🔭 Surveying document (Omni-Mode): {Path(file_path).name}")
        
        sample_text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                # Get a distributed sample: First 3 Pages, Middle Page, Last 2 Pages
                pages_to_sample = []
                total_pages = len(pdf.pages)
                
                # First 3 pages
                for i in range(min(3, total_pages)):
                    pages_to_sample.append(i)
                
                # Middle page
                if total_pages > 4:
                    pages_to_sample.append(total_pages // 2)
                
                # Last 2 pages (avoid duplicates)
                for i in range(max(0, total_pages - 2), total_pages):
                    if i not in pages_to_sample:
                        pages_to_sample.append(i)
                
                pages_to_sample.sort()
                
                sampled_lines = []
                for p_idx in pages_to_sample:
                    text = pdf.pages[p_idx].extract_text()
                    if text:
                        # Full text of these pages
                        lines = text.split('\n')
                        sampled_lines.extend(lines)
                        sampled_lines.append("... [PAGE BREAK] ...")
                
                sample_text = "\n".join(sampled_lines)

        except Exception as e:
            logger.error(f"   ❌ Failed to read PDF: {e}")
            return []
        
        prompt = f"""You are a Python Regex Expert. Analyze this financial document sample.
It contains mixed transaction types (Trading, Dividends, Transfers).
Some fields are COMPRESSED (joined by '@' or no space, e.g. 'Acquista100@50,20').

SAMPLE TEXT:
{sample_text}

TASK:
1. Identify ALL distinct `start_keywords` that mark new events (e.g. "Contrattazione", "Dividendi", "Deposito", "Prelievo").
2. For each keyword, define extraction rules.
3. **CRITICAL**: Handle COMPRESSED formats. 
   - If text is `Acquista1@155,29`, use regex: `(?P<operation>Acquista)(?P<quantity>\\d+)@(?P<price>[\\d,]+)`
   - Ticker usually follows start keyword. Regex lookbehind: `(?<={{start_keyword}}\\s)(?P<ticker>.*?)(\\s(Acquista|Vendi)|$)`
   - ISIN: Check if usually on next line (offset 1).

RESPONSE JSON Format:
{{
  "schemas": [
    {{
      "type": "TRADING",
      "start_keyword": "Contrattazione",
      "fields": {{
        "ticker": {{ "line_offset": 0, "regex": "..." }},
        "isin":     {{ "line_offset": 1, "regex": "\\s*(?P<isin>[A-Z]{2}[A-Z0-9]{9}\\d)" }},
        "compressed_data": {{ "line_offset": 0, "regex": "(?P<op>Acquista|Vendi)(?P<qty>-?\\d+)@(?P<price>[\\d,]+)" }} 
      }}
    }},
    {{
      "type": "DIVIDEND",
      "start_keyword": "Dividendo",
      "fields": {{ ... }}
    }}
  ]
}}
"""

        response = self._call_ollama(prompt, json_mode=True)
        if response:
            try:
                clean_response = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_response)
                # LLM sometimes returns object with 'schemas' key, sometimes list. Handle both.
                if isinstance(data, dict) and 'schemas' in data:
                    self.schemas = data['schemas']
                elif isinstance(data, list):
                    self.schemas = data
                else:
                    self.schemas = []
                    
                logger.info(f"   ✅ Discovered {len(self.schemas)} Schemas")
                logger.debug(str(self.schemas))
                return self.schemas
            except Exception as e:
                logger.error(f"   ❌ Invalid JSON rules: {e}")
        
        return []

    def extract_transactions(self, file_path: str) -> List[Dict]:
        """
        Phase 2: Omni-Miner (Block-Based Strategy)
        Accumulates lines into blocks defined by Start Keywords, 
        then scans the full block for data (ISIN, Ticker, etc).
        """
        if not self.schemas:
            return []
            
        logger.info("⚡ Executing extraction with Block-Based strategy...")
        transactions = []
        
        # Prepare Keywords map
        # Map lower-case start keyword to Schema
        schema_map = {}
        for schema in self.schemas:
            kw = schema.get('start_keyword', '').lower()
            if kw: schema_map[kw] = schema

        current_date = None
        current_block = []
        current_schema = None
        current_raw_anchor = ""
        
        # Date Regex (dd-mmm-yyyy or dd/mm/yyyy)
        date_regex = re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[a-zA-Z]{3}-\d{2,4})\b')
        
        # Helper to process a finished block
        def process_block(lines, schema, raw_anchor, date_ctx):
            if not lines or not schema: return
            
            block_text = "\n".join(lines)
            t_data = {'type': schema.get('type', 'UNKNOWN'), 'raw_anchor': raw_anchor}
            if date_ctx: t_data['date'] = date_ctx

            # 1. Ticker / Main Line Data (Usually on the first line or anchor)
            # Use the compressed regex from discovery if available
            main_fields = schema.get('fields', {})
            
            # Apply "Compressed Data" regex on the Anchor Line (First line)
            if 'compressed_data' in main_fields:
                rule = main_fields['compressed_data']
                match = re.search(rule['regex'], raw_anchor, re.IGNORECASE)
                if match:
                    t_data.update(match.groupdict())

            # Specific Ticker Regex (on Anchor)
            if 'ticker' in main_fields:
                rule = main_fields['ticker']
                match = re.search(rule['regex'], raw_anchor, re.IGNORECASE)
                if match:
                    val = match.group('ticker')
                    # Clean start keyword from ticker if accidentally captured
                    start_kw = schema.get('start_keyword', '')
                    if val and start_kw: 
                        val = val.replace(start_kw, "").strip()
                    t_data['ticker'] = val

            # 2. ISIN Scan (Anywhere in Block)
            # Robust Regex: 2 Letters + 9 Alphanum + 1 Digit (Check digit usually number)
            # But many ISINs end with letter? Actually standard is 12 chars.
            # Strictly: [A-Z]{2}[A-Z0-9]{9}\d. 
            # Let's use a slightly broader one but strictly 12 chars starting with Country Code.
            isin_match = re.search(r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b', block_text)
            if isin_match:
                t_data['isin'] = isin_match.group(1)
            
            # 3. Cleanup & Normalize
            if 'price' in t_data: t_data['price'] = t_data['price'].replace('USD','').replace('EUR','').strip()
            if 'qty' in t_data: t_data['quantity'] = t_data['qty']
            
            if 'ticker' in t_data or 'isin' in t_data:
                transactions.append(t_data)

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                lines = text.split('\n')
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if not line: 
                        i += 1
                        continue

                    # Check for Date Header (Context)
                    # Only if line is short to avoid false positives in long text
                    if len(line) < 40:
                        d_match = date_regex.search(line)
                        if d_match:
                            current_date = d_match.group(0)
                    
                    # Check for Start Keyword (Start of NEW Block)
                    found_schema = None
                    for kw, schema in schema_map.items():
                        if line.lower().startswith(kw):
                            found_schema = schema
                            break
                    
                    if found_schema:
                        # Process PREVIOUS block
                        if current_block:
                            process_block(current_block, current_schema, current_raw_anchor, current_date)
                        
                        # Start NEW block
                        current_block = [line] # Include anchor in block text? Yes.
                        current_raw_anchor = line
                        current_schema = found_schema
                    else:
                        # Add to CURRENT block
                        if current_block:
                            current_block.append(line)
                            
                    i += 1

            # Process FINAL block
            if current_block:
                process_block(current_block, current_schema, current_raw_anchor, current_date)

        logger.info(f"   ✅ Extracted {len(transactions)} transactions")
        return transactions

    def parse(self, file_path: str) -> List[Dict]:
        self.discover_structure(file_path)
        return self.extract_transactions(file_path)

if __name__ == "__main__":
    f = r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo\Transactions_19807401_2024-11-26_2025-12-19.pdf"
    parser = DynamicPDFParser()
    res = parser.parse(f)
    print(f"Extracted {len(res)} transactions")
    
    with open("debug_parser_output.json", "w") as f_out:
        json.dump({"schemas": parser.schemas, "transactions": res}, f_out, indent=2, default=str)
