import os
import json
import logging
import requests
import pandas as pd
from pathlib import Path
import pdfplumber 
import time
import re

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
INPUT_FOLDER = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox")
OUTPUT_FOLDER = Path(__file__).resolve().parent.parent / 'data' / 'extracted'
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 10 

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# PROMPTS
# =============================================================================

PROMPT_CSV_DIRECT = """You are a Data Processor.
Convert this CSV segment into a JSON array of holdings.

INSTRUCTIONS:
1. Analyze the content row by row.
2. Map columns to standard fields: ticker, name, isin, quantity, price, currency, date.
3. Return a JSON list of objects.

CRITICAL RULES:
- **EXTRACT REAL DATA ONLY**: Do NOT output example data (No Apple/AAPL). Use ONLY the rows present in the CSV content below.
- **Header Parsing**: The first line of the content might be the header.
- **Output Format**: JSON List only.

CSV CONTENT:
{content}
"""

PROMPT_CSV_FULL = """You are a Portfolio Analyzer.
The CSV below contains holdings organized by Asset Type sections (e.g. 'Azioni', 'ETF', 'Obbligazioni').

TASK:
Extract all holdings into a single JSON list.

CRITICAL INSTRUCTION - ASSET CLASSIFICATION:
For each item, identify its **asset_type** based on the SECTION HEADER above it in the file.
- Header "Azioni" or similar -> Set asset_type="STOCK"
- Header "ETF" or similar -> Set asset_type="ETF"
- Header "Obbligazioni" or similar -> Set asset_type="BOND"
- Header "Liquidità" or similar -> Set asset_type="CASH"
- Header "Opzioni" -> Set asset_type="OPTION"
- Header "Fondi" -> Set asset_type="FUND"

OUTPUT FORMAT (JSON List):
[
  {{ "ticker": "...", "name": "...", "isin": "...", "quantity": ..., "currency": "...", "asset_type": "STOCK", "current_price": ... }}
]

CSV CONTENT:
{content}
"""

PROMPT_PDF_EXTRACTION = """You are a Financial Data Extractor.
Analyze the document text below.

TASK:
1. Identify **Document Type**: 'HOLDINGS' (Portfolio Statement) or 'TRANSACTIONS' (Trade Confirmation/History).
2. Extract the data into a JSON list.

IF HOLDINGS (Current Assets):
Extract: ticker, isin, name, quantity, currency, purchase_price (cost basis), current_value.

IF TRANSACTIONS (History):
Extract: date (YYYY-MM-DD), type (BUY/SELL), ticker, isin, quantity, price, total_amount, currency.

RETURN ONLY JSON (No Markdown):
{{
  "document_type": "HOLDINGS",
  "data": [
    {{ "ticker": "AAPL", "quantity": 10 }}
  ]
}}

DOCUMENT TEXT:
{content}
"""

# Load Prompts from JSON
try:
    with open(Path(__file__).parent / "ingestion_prompts.json", "r", encoding="utf-8") as f:
        prompts = json.load(f)
        PROMPT_REGEX_DISCOVERY = prompts.get("PROMPT_REGEX_DISCOVERY", "")
        PROMPT_CSV_ANALYSIS = prompts.get("PROMPT_CSV_ANALYSIS", "")
        # Fallback if missing
        if not PROMPT_CSV_ANALYSIS:
            PROMPT_CSV_ANALYSIS = "Sei un analista finanziario..." # Fallback hardcoded minimal
except Exception as e:
    print(f"❌ Error loading prompts: {e}")
    PROMPT_REGEX_DISCOVERY = ""
    PROMPT_CSV_ANALYSIS = ""

# =============================================================================
# LLM UTILS
# =============================================================================

def call_ollama(prompt, context=""):
    print(f"\n[{context}] 📤 SENDING PROMPT TO {OLLAMA_MODEL}:")
    print("-" * 40)
    print(prompt[:1000] + ("..." if len(prompt) > 1000 else ""))
    print("-" * 40)

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=300
        )
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            print(f"\n[{context}] 📥 RECEIVED RESPONSE:")
            print("-" * 40)
            print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
            print("-" * 40)
            return response_text
        else:
            logger.error(f"Error calling Ollama: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        logger.error(f"Exception calling Ollama: {e}")
        return None

def parse_json_response(response_text):
    try:
        # Try finding first [ and last ] for list
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = response_text[start:end]
            return json.loads(json_str)
        
        # Fallback to finding { and } if it wrapped it in object
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
             data = json.loads(response_text[start:end])
             # If wrapped in key "holdings" or "data", extract it
             if isinstance(data, dict):
                 for key in ["holdings", "data", "items"]:
                     if key in data and isinstance(data[key], list):
                         return data[key]
                 # If just a dict, maybe one item?
                 return [data]
        return []
    except json.JSONDecodeError:
        logger.error(f"JSON Decode Error on: {response_text[:100]}")
        return []

def extract_json_object(response_text):
    # Specialized for PDF response which is an Object, not a List
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(response_text[start:end])
    except:
        pass
    return {}

# =============================================================================
# HANDLERS
# =============================================================================

def process_csv_direct(filepath):
    """
    Directly extracts data using Hybrid Strategy (Section Splitting + LLM).
    Splits CSV by Section Headers (e.g. "Azioni (n)", "ETP (n)") and forces asset_type.
    """
    logger.info(f"   --> Processing CSV (Hybrid Smart Split): {filepath.name}")
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        if not lines:
            return

        header_line = lines[0].strip()
        all_items = []
        
        # 1. Parse Sections via Regex
        sections = []
        current_section_name = "STOCK" # Default
        current_rows = []
        
        # Regex for "Name (Count)" e.g. "Azioni (48)", "ETP (7)"
        section_regex = re.compile(r'^"([A-Za-z /]+) \(\d+\)"')
        
        # Start from line 1 (skip header)
        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            
            # Check for Section Header
            # Logic: If line matches regex AND has empty subsequent columns (usually)
            # But line 2 in CSV was `"Azioni (48)","","",""...`
            m = section_regex.match(line)
            if m:
                # Flush previous section
                if current_rows:
                    sections.append((current_section_name, current_rows))
                    current_rows = []
                
                # Set new section
                raw_name = m.group(1).upper()
                if "AZIONI" in raw_name: current_section_name = "STOCK"
                elif "ETF" in raw_name or "ETP" in raw_name: current_section_name = "ETF"
                elif "OBBLIGAZIONI" in raw_name: current_section_name = "BOND"
                elif "FONDI" in raw_name: current_section_name = "FUND"
                elif "LIQUIDIT" in raw_name: current_section_name = "CASH"
                elif "OPZIONI" in raw_name: current_section_name = "OPTION"
                else: current_section_name = "STOCK" # Fallback
                
                logger.info(f"   Found Section: {raw_name} -> {current_section_name}")
                continue
            
            # Add Row
            current_rows.append(line)
            
        # Flush last
        if current_rows:
            sections.append((current_section_name, current_rows))
            
        # 2. Process Each Section
        for sec_type, rows in sections:
            logger.info(f"   Processing Section {sec_type} ({len(rows)} rows)...")
            
            # Chunking within section if needed (e.g. > 50 rows)
            # For now, assume section fits context (usually < 50)
            chunk_size = 30
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i : i + chunk_size]
                
                content = header_line + "\n" + "\n".join(chunk)
                
                # Append Instruction to Prompt
                prompt = PROMPT_CSV_DIRECT.format(content=content)
                prompt += f"\n\nIMPORTANT: You must set the 'asset_type' field to '{sec_type}' for ALL items in this list."
                
                response = call_ollama(prompt, context=f"SEC_{sec_type}_{i}")
                if response:
                    items = parse_json_response(response)
                    if items:
                         # Reinforce type in python just in case LLM ignored it
                        for x in items:
                            x['asset_type'] = sec_type
                        all_items.extend(items)
                
                time.sleep(1)

        # Save Result
        if all_items:
            # Add broker metadata
            for item in all_items:
                if 'broker' not in item:
                    item['broker'] = filepath.parent.name
                    
            out_path = OUTPUT_FOLDER / f"{filepath.name}.json"
            logger.info(f"   Saving to: {out_path}")
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "broker": filepath.parent.name, 
                    "source_file": filepath.name,
                    "strategy": "Hybrid Smart Split",
                    "items_count": len(all_items),
                    "data": all_items
                }, f, indent=2)
                
            return out_path
            
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        return None

import sys
# Ensure we can import local modules
sys.path.append(str(Path(__file__).parent.parent))
from scripts.universal_pdf_parser import parse_pdf

def process_pdf_direct(filepath):
    """
    Directly extracts data using appropriate strategy.
    Strategy A: BG SAXO Transactions -> Deterministic Parser (Regex Rules)
    Strategy B: Generic -> LLM Extraction
    """
    logger.info(f"   --> PDF Strategy: {filepath.name}")
    
    # STRATEGY A: BG SAXO TRANSACTIONS (Deterministic V2)
    if "Transactions" in filepath.name and "bgsaxo" in str(filepath.parent).lower():
         logger.info("   🚀 DETECTED BG SAXO TRANSACTIONS: Switching to Deterministic Parser V2")
         try:
             # Import V2 Parser
             from scripts.universal_pdf_stream_parser_v2 import clean_text, parse_lines
             
             # Execute
             clean_lines = clean_text(str(filepath))
             txns = parse_lines(clean_lines)
             
             if txns:
                 out_path = OUTPUT_FOLDER / f"{filepath.name}.json"
                 with open(out_path, 'w', encoding='utf-8') as f:
                     json.dump({
                        "broker": filepath.parent.name,
                        "source_file": filepath.name,
                        "document_type": "TRANSACTIONS",
                        "items_count": len(txns),
                        "data": txns
                     }, f, indent=2, default=str)
                 logger.info(f"✅ Saved output to: {out_path.name} ({len(txns)} items)")
                 return out_path
         except Exception as e:
             logger.error(f"Deterministic Parse V2 Failed: {e}. Falling back to LLM...")

    # STRATEGY: SELF-LEARNING REGEX (LLM Discovery -> Python Execution)
    all_items = []
    doc_type = "TRANSACTIONS" # Defaulting for this workflow
    full_text_pages = []

    try:
        # 1. READ FULL PDF TEXT
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text_pages.append(t)
        
        if not full_text_pages:
            logger.error("   ❌ No text extracted from PDF.")
            return None

        # 2. DISCOVERY (Sample first 6 pages to learn structure)
        sample_pages = full_text_pages[:6]
        sample_text = "\n".join(sample_pages)
        
        logger.info(f"   🧠 ANALYZING STRUCTURE (Sample: {len(sample_pages)} pages)... asking LLM for Regex.")
        
        prompt = PROMPT_REGEX_DISCOVERY.format(content=sample_text[:12000]) # Increased
        response = call_ollama(prompt, context="REGEX_GENERATION")
        
        # Parse JSON
        try:
            if "```json" in response:
                clean_json = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                clean_json = response.split("```")[1].split("```")[0].strip()
            else:
                clean_json = response.strip()
                
            regex_result = json.loads(clean_json)
            
            # Support both 'patterns' list (New) and 'regex_pattern' string (Legacy)
            patterns_list = []
            if "patterns" in regex_result and isinstance(regex_result["patterns"], list):
                for p in regex_result["patterns"]:
                    if "regex" in p:
                        patterns_list.append((p.get("name", "Unknown"), p["regex"]))
            elif "regex_pattern" in regex_result:
                patterns_list.append(("Single Pattern", regex_result["regex_pattern"]))
                
            if not patterns_list:
                logger.error("❌ No regex patterns found in LLM response.")
                return None

        except json.JSONDecodeError:
            logger.error("❌ Failed to parse JSON from LLM.")
            return None

        # Apply ALL Regex patterns
        all_transactions = []
        seen_positions = set() # To avoid duplicates if regexes overlap
        
        logger.info(f"   ⚡ APPLYING {len(patterns_list)} REGEX PATTERNS...")
        
        full_doc_text = "\n".join(full_text_pages) # Ensure full_doc_text is defined here
        
        for name, pattern_str in patterns_list:
            try:
                logger.info(f"     👉 Pattern '{name}': {pattern_str[:50]}...")
                regex = re.compile(pattern_str, re.DOTALL | re.IGNORECASE)
                
                matches = list(re.finditer(regex, full_doc_text))
                count = 0
                
                for m in matches:
                    # Deduplicate by start index (heuristic)
                    if m.start() in seen_positions:
                        continue
                    seen_positions.add(m.start())
                    
                    item = m.groupdict()
                    # Clean whitespace
                    for k, v in item.items():
                        if v: item[k] = v.strip()
                    
                    all_transactions.append(item)
                    count += 1
                    
                logger.info(f"        ✅ Captured {count} items.")
                
            except re.error as e:
                logger.error(f"     ❌ Invalid Regex '{name}': {e}")

        logger.info(f"   ✅ TOTAL UNIQUES TRANSACTIONS: {len(all_transactions)}!")
        all_items = all_transactions # Assign to all_items for later saving

    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return None

    # Save
    if all_items:
        out_path = OUTPUT_FOLDER / f"{filepath.name}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump({
                "broker": filepath.parent.name,
                "source_file": filepath.name,
                "document_type": doc_type,
                "items_count": len(all_items),
                "data": all_items
            }, f, indent=2)
        logger.info(f"✅ Saved output to: {out_path.name} ({len(all_items)} items)")
    else:
        logger.warning("   ⚠️ No items matched the generated regex.")

def process_file_router(filepath, broker):
    ext = filepath.suffix.lower()
    if ext == ".csv":
        process_csv_direct(filepath)
    elif ext == ".pdf":
        process_pdf_direct(filepath)
    else:
        logger.info(f"   ⏭️ Skipping unsupported file type: {ext}")

def main():
    print("🚀 UNIVERSAL ROUTER STARTING")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Scanning: {INPUT_FOLDER}")
    
    if not INPUT_FOLDER.exists():
        logger.error("Input folder not found!")
        return

    target_dir = INPUT_FOLDER / "bgsaxo"
    files = list(target_dir.glob("*"))
    print(f"Found {len(files)} files in bgsaxo.")
    
    for f in files:
        if f.name.startswith("~$"): continue
        print("\n" + "="*60)
        print(f"📄 Processing: {f.name}")
        
        process_file_router(f, target_dir.name)
        print("-"*60)

if __name__ == "__main__":
    main()
