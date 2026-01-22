import sys
import json
import logging
import pdfplumber
from pathlib import Path
from ingestion_lib import call_ollama, parse_json_garbage

# CONFIG
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
PROMPTS_FILE = Path(__file__).parent / "ingestion_prompts.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("TR_Holdings")

def load_prompts():
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_holdings_text(pdf_path):
    """
    Trade Republic holdings are usually on the LAST page 
    under 'PANORAMICA DEL SALDO'.
    """
    with pdfplumber.open(pdf_path) as pdf:
        # Check last 2 pages in case it's long
        text = ""
        total_pages = len(pdf.pages)
        start_page = max(0, total_pages - 2)
        for i in range(start_page, total_pages):
            text += f"--- PAGE {i+1} ---\n"
            text += pdf.pages[i].extract_text(layout=True) + "\n"
        return text

def extract_holdings(pdf_path):
    logger.info(f"🔍 Extracting holdings from: {pdf_path.name}")
    
    # 1. Get Text
    content = extract_holdings_text(pdf_path)
    if not content:
        logger.error("   ❌ No text extracted from PDF.")
        return None
        
    # 2. Call LLM
    prompts = load_prompts()
    prompt = prompts["PROMPT_TR_HOLDINGS"].replace("{content}", content)
    
    logger.info("   🧠 Asking Qwen to parse holdings table...")
    resp = call_ollama(prompt, context="TR_HOLDINGS", model=OLLAMA_MODEL)
    
    if not resp:
        logger.error("   ❌ LLM failed to respond.")
        return None
        
    # 3. Parse JSON
    data = parse_json_garbage(resp)
    if data:
        out_file = pdf_path.with_suffix('.holdings.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"   ✅ Extracted {len(data)} holdings to: {out_file.name}")
        return data
    else:
        logger.error("   ❌ Failed to parse holdings JSON from LLM response.")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_tr_holdings.py <pdf_file>")
        sys.exit(1)
    
    extract_holdings(Path(sys.argv[1]))
