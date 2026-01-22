import sys
import json
import logging
import requests
import pdfplumber
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.ingestion_lib import parse_json_garbage

# CONFIG
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"
PROMPTS_FILE = Path(__file__).parent / "ingestion_prompts.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("TR_Analyzer")

def load_prompts():
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_text_sample(pdf_path, pages=2):
    """Extracts first N pages for classification & analysis."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:pages]):
            text += f"--- PAGE {i+1} ---\n"
            text += page.extract_text(layout=True) + "\n"
    return text

def unload_model():
    """Forces Ollama to unload the current model from VRAM."""
    try:
        requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "keep_alive": 0}, timeout=10)
        logger.info("   🧹 VRAM cleared (Model unloaded).")
    except:
        pass

def call_ollama(prompt, context=""):
    logger.info(f"   📤 Asking LLM ({context})...")
    max_retries = 2
    for attempt in range(max_retries):
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
                timeout=300 # Increased to 5 minutes to accommodate slow model loading
            )
            if resp.status_code == 200:
                return resp.json().get('response', '')
            else:
                logger.error(f"   ❌ LLM Error: {resp.status_code}")
        except requests.exceptions.Timeout:
            logger.warning(f"   ⏳ Ollama timed out (300s). Attempt {attempt+1}/{max_retries}")
            unload_model() # Clear VRAM on timeout/error
        except Exception as e:
            logger.error(f"   ❌ LLM Exception: {e}")
            unload_model()
            
        if attempt < max_retries - 1:
            import time
            logger.info("      🔄 Retrying in 5s...")
            time.sleep(5)
            
    return None

def analyze_structure(pdf_path):
    prompts = load_prompts()
    
    # 1. READ TEXT (Sample for classification, more for rules)
    logger.info(f"📖 Reading {pdf_path.name}...")
    sample_content = extract_text_sample(pdf_path, pages=2)
    full_sample = extract_text_sample(pdf_path, pages=8) # More for rule discovery
    
    if not sample_content:
        logger.error("   ❌ No text found.")
        return

    # 2. CLASSIFY (The Router)
    print(f"\n{'='*60}")
    print(f" 🚦 PHASE 1: THE ROUTER (Classification)")
    print(f"{'='*60}")
    
    logger.info("Asking LLM to classify document sections...")
    class_prompt = prompts["PROMPT_DOC_CLASSIFICATION"].replace("{content}", sample_content)
    class_resp = call_ollama(class_prompt, "CLASSIFICATION")
    
    classification = {
        "doc_type": "UNKNOWN",
        "has_transactions": False,
        "has_holdings": False,
        "confidence": 0,
        "reasoning": "Failed to parse"
    }
    
    try:
        parsed = parse_json_garbage(class_resp)
        if parsed:
            classification.update(parsed)
    except Exception as e:
        logger.warning(f"   ⚠️ Error parsing classification: {e}")

    # KEYWORD-BASED FALLBACK (If LLM fails or is unsure)
    if classification["doc_type"] == "UNKNOWN" or not classification["has_transactions"]:
        if "DATA TIPO DESCRIZIONE" in sample_content.upper() or "IN ENTRATA" in sample_content.upper():
            logger.info("   🔍 Fallback: Found Transaction keywords. Setting has_transactions=True")
            classification["has_transactions"] = True
            classification["doc_type"] = "TRANSACTIONS"
            
    if classification["doc_type"] == "UNKNOWN" or not classification["has_holdings"]:
        if "PANORAMICA DEL SALDO" in sample_content.upper() or "VALORE DI MERCATO" in sample_content.upper():
            logger.info("   🔍 Fallback: Found Holdings keywords. Setting has_holdings=True")
            classification["has_holdings"] = True
            if classification["doc_type"] == "TRANSACTIONS":
                classification["doc_type"] = "MIXED"
            else:
                classification["doc_type"] = "HOLDINGS"

    logger.info(f"   👉 FINAL DECISION: {classification['doc_type']} (T:{classification['has_transactions']}, H:{classification['has_holdings']})")
    logger.info(f"   📝 REASONING: {classification.get('reasoning')}")

    # Save classification for the master orchestrator
    class_file = pdf_path.with_suffix('.classification.json')
    with open(class_file, 'w', encoding='utf-8') as f:
        json.dump(classification, f, indent=2)
    logger.info(f"   💾 Classification saved to: {class_file.name}")

    # 3. RULE GENERATION (Only if transactions are present)
    if classification["has_transactions"]:
        print(f"\n{'='*60}")
        print(f" 🧠 PHASE 2: RULE GENERATOR (Regex Discovery)")
        print(f"{'='*60}")
        
        logger.info("🧠 Generating Parsing Rules for Transactions...")
        rule_prompt = prompts["PROMPT_TR_RULE_DISCOVERY"].replace("{content}", full_sample)
        rule_resp = call_ollama(rule_prompt, "RULE_GENERATION")
        
        if rule_resp:
            try:
                rules = parse_json_garbage(rule_resp)
                if rules:
                    # Save rules
                    out_file = pdf_path.with_suffix('.pdf.rules.json')
                    with open(out_file, 'w', encoding='utf-8') as f:
                        json.dump(rules, f, indent=2)
                    logger.info(f"   ✅ Rules saved to: {out_file.name}")
            except Exception as e:
                logger.error(f"   ❌ Failed to parse Rules JSON: {e}")
    else:
        logger.info("   ℹ️ No transactions section detected. Skipping rule generation.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_tr_structure.py <pdf_file>")
        sys.exit(1)
    
    analyze_structure(Path(sys.argv[1]))
