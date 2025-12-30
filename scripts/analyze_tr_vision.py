import sys
import json
import base64
import requests
import logging
from pathlib import Path
from pdf2image import convert_from_path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from poppler_config import POPPLER_PATH
from io import BytesIO

import time
from PIL import Image

# CONFIG
OLLAMA_URL = "http://localhost:11434"
VISION_MODEL = "llama3.2-vision:11b"
TEXT_MODEL = "qwen2.5:14b-instruct-q6_K"
PROMPTS_FILE = Path(__file__).parent / "ingestion_prompts.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("TR_Vision_Analyzer")

def pdf_pages_to_images(pdf_path, page_indices):
    """Convert specific PDF pages to PIL images."""
    logger.info(f"Converting PDF pages {page_indices} to images...")
    try:
        # Convert all pages first
        all_images = convert_from_path(pdf_path, dpi=110, poppler_path=POPPLER_PATH)
        
        # Select only requested pages
        selected = [all_images[i] for i in page_indices if i < len(all_images)]
        logger.info(f"   ✅ Converted {len(selected)} pages")
        return selected
    except Exception as e:
        logger.error(f"   ❌ PDF conversion failed: {e}")
        return []

def image_to_base64(image):
    """Convert PIL image to base64 string after resizing for optimization."""
    # Resize for optimization (Llama 3.2 Vision works well with ~1120px)
    max_size = 1000
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    logger.info(f"      Resized image to: {image.size}")
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def call_ollama(prompt, model, images=None, format_json=False):
    """Generic call to Ollama - optimized for lightweight vision."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m", # Keep in memory by default to reduce overhead
        "options": {
            "temperature": 0.0,
            "num_predict": 1000, 
            "num_ctx": 4096      
        }
    }
    if format_json:
        payload["format"] = "json"
    if images:
        payload["images"] = images
        
    try:
        # Standard timeout for quick response
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json().get('response', '')
        else:
            logger.error(f"   ❌ Ollama Error ({model}): {resp.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.warning(f"   ⏳ Ollama timed out (120s). Forcing VRAM unload to recover...")
        unload_model(model)
        return None
    except Exception as e:
        logger.error(f"   ❌ Ollama Exception: {e}")
        return None

def extract_json(text):
    """Robustly extract JSON from model output even if there is chatter."""
    try:
        # Try finding the first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text
    except:
        return text

def unload_model(model_name):
    """Tell Ollama to unload the model to free VRAM."""
    try:
        requests.post(f"{OLLAMA_URL}/api/generate", json={"model": model_name, "keep_alive": 0}, timeout=10)
    except:
        pass

def consolidate_findings(findings):
    """Programmatically synthesize findings into final rules."""
    logger.info("🔧 Consolidating findings programmatically...")
    
    # Filter out empty or raw responses that failed to parse
    valid_findings = [f for f in findings if isinstance(f, dict) and ("strategy_config" in f or "keywords_found" in f)]
    if not valid_findings:
        logger.warning("⚠️ No valid findings to consolidate!")
        return None

    # Initialize containers
    all_types = set()
    regex_pools = {
        "date_header": [],
        "line_start": [],
        "date_field": [],
        "type_field": [],
        "amount_field": []
    }
    
    for f in valid_findings:
        # 1. Keywords
        keywords = f.get("keywords_found", [])
        if isinstance(keywords, list):
            clean = [k.strip() for k in keywords if k.lower() not in ["etc", "...", "type", "keyword1", "keyword2"]]
            all_types.update(clean)
            
        # 2. Strategy Config
        config = f.get("strategy_config", {})
        if config.get("date_header_regex"): regex_pools["date_header"].append(config["date_header_regex"])
        if config.get("line_start_regex"): regex_pools["line_start"].append(config["line_start_regex"])
        
        # 3. Field Extractors
        extractors = f.get("field_extractors", {})
        if extractors.get("date", {}).get("regex"): regex_pools["date_field"].append(extractors["date"]["regex"])
        if extractors.get("type", {}).get("regex"): regex_pools["type_field"].append(extractors["type"]["regex"])
        if extractors.get("amount", {}).get("regex"): regex_pools["amount_field"].append(extractors["amount"]["regex"])

    def most_frequent(lst, default):
        # Filter placeholders and very specific strings (heuristic: must contain a backslash or digit class)
        real_ones = [x for x in lst if x and "\\" in x and "..." not in x]
        if not real_ones: 
            # If no generic regex, maybe they gave a generic pattern like [0-9]
            real_ones = [x for x in lst if x and any(c in x for c in "[]+.")]
        
        if not real_ones: return default
        return max(set(real_ones), key=real_ones.count)

    discovered_types = sorted(list(all_types))
    # Ensure discovered types are valid regex part
    safe_types = [t for t in discovered_types if t and len(t) > 2]
    
    # REFINEMENT: Always use the UNION of all safe types to avoid missing transactions
    # that Llama might have missed in a single-page analysis.
    all_types_pipe = "|".join(safe_types) if safe_types else "Bonifico|Commercio|Acquisto|Vendita|Interessi|Dividendi|Imposta|Rendita"
    type_regex = "(" + all_types_pipe + ")"

    # MONTHS REGEX (Italian/English common for TR)
    months_pattern = r"(?:GEN|FEB|MAR|APR|MAG|GIU|LUG|AGO|SET|OTT|NOV|DIC|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    
    # REFINEMENT: Ensure line_start starts with \s*
    def ensure_layout_robust(regex):
        if not regex: return regex
        if regex.startswith("^") and not regex.startswith(r"^\s*"):
            return r"^\s*" + regex[1:]
        return regex

    # Force a robust line start that includes all triggers
    # Use \s+ for the space between day and month
    default_line_start = r"^\s*(?:\d{1,2}\s+" + months_pattern + r"|" + all_types_pipe + ")"

    final_rules = {
        "strategy": "line_stateful",
        "strategy_config": {
            "date_header_regex": r"^\s*\d{1,2}\s+" + months_pattern + r"(?:\s+\d{4})?\s*$",
            "line_start_regex": default_line_start, 
            "multiline_continuation": True
        },
        "field_extractors": {
            "date": { "regex": r"\d{1,2}\s+" + months_pattern },
            "type": { "regex": type_regex },
            "description": { "regex": r".*" },
            "amount": { "regex": most_frequent(regex_pools["amount_field"], r"-?\d{1,3}(?:\.\d{3})*(?:,\d{2})\s?€?") }
        }
    }
    
    print(f"\n📊 DISCOVERED TRANSACTION TYPES: {', '.join(safe_types)}")
    return json.dumps(final_rules)

def analyze_with_vision(pdf_path):
    """Main analysis using vision model (page by page)."""
    
    print(f"\n{'='*60}")
    print(f" 👁️  VISION-BASED ANALYSIS (Lightweight)")
    print(f"{'='*60}")
    
    logger.info("🧹 Clearing VRAM before starting...")
    unload_model(VISION_MODEL)
    
    from pdf2image import pdfinfo_from_path
    info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
    total_pages = info['Pages']
    
    indices = set()
    for i in range(min(4, total_pages)): indices.add(i)
    if total_pages > 4:
        mid = total_pages // 2
        indices.add(mid)
        if mid + 1 < total_pages: indices.add(mid + 1)
    for i in range(max(0, total_pages - 3), total_pages): indices.add(i)
    page_indices = sorted(list(indices))
        
    logger.info(f"📖 Analyzing pages {[p+1 for p in page_indices]} of {pdf_path.name}...")
    images = pdf_pages_to_images(pdf_path, page_indices)
    
    if not images:
        logger.error("   ❌ No images extracted")
        return

    findings = []
    # GENERIC REGEX PROMPT
    vision_prompt = """Analyze this Trade Republic statement page.
Identify every TRANSACTION TYPE keyword (e.g., Bonifico, Commercio, Acquisto, Vendita, Interessi, Imposta, Dividendi).
Determine the structure for a generic Python parser.

YOUR TASK:
Return GENERIC Python regex patterns, NOT specific values.
Example: use '\\d{1,2} [A-Z]{3}' instead of '19 SET'.

Response format:
KEYWORDS: [comma separated list of actual transaction types found]
DATE_FORMAT: [actual values seen]
JSON: {
  "keywords_found": ["type1", "type2"],
  "strategy_config": {
    "date_header_regex": "^\\\\s*\\\\d{1,2}\\\\s\\\\w{3}(?:\\\\s\\\\d{4})?\\\\s*$",
    "line_start_regex": "^\\\\s*(?:\\\\d{1,2}\\\\s\\\\w{3}|Type1|Type2)"
  },
  "field_extractors": {
    "date": {"regex": "\\\\d{1,2}\\\\s\\\\w{3}"},
    "type": {"regex": "(Type1|Type2)"},
    "amount": {"regex": "-?\\\\d{1,3}(?:\\\\.\\\\d{3})*(?:,\\\\d{2})\\\\s€"}
  }
}"""

    debug_dir = Path("debug_vision")
    debug_dir.mkdir(exist_ok=True)

    for i, img in enumerate(images):
        page_num = page_indices[i] + 1
        logger.info(f"   🖼️  Analyzing Page {page_num}...")
        
        if i > 0:
            logger.info(f"      ⏸️  Pausing 5s to stabilize memory...")
            time.sleep(5)
            
        for attempt in range(2):
            max_size = 1000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img_proc = img.resize(new_size, Image.Resampling.LANCZOS)
            else:
                img_proc = img
            
            debug_img_path = debug_dir / f"page_{page_num}_resized.png"
            img_proc.save(debug_img_path)

            # WE DISABLE NATIVE JSON MODE to avoid stalling. We will extract JSON ourselves.
            resp_raw = call_ollama(vision_prompt, VISION_MODEL, images=[image_to_base64(img_proc)], format_json=False)
            
            if resp_raw:
                try:
                    clean_json = extract_json(resp_raw)
                    data = json.loads(clean_json)
                    keywords = data.get('keywords_found', [])
                    print(f"      ✅ Page {page_num} Finding: {len(keywords)} types -> {', '.join(keywords[:5])}...")
                    findings.append(data)
                    break 
                except Exception as e:
                    logger.error(f"      ❌ Page {page_num}: Invalid JSON response")
                    if "Page 4" in f"Page {page_num}":
                        logger.debug(f"         RAW: {resp_raw[:200]}...")
                    unload_model(VISION_MODEL)
            
            if attempt == 0:
                logger.warning(f"      ⚠️  Attempt 1 failed. Forcing reset and retrying in 10s...")
                unload_model(VISION_MODEL)
                time.sleep(10)
            else:
                logger.error(f"      ❌ Page {page_num} failed both attempts.")

    final_rules_json = consolidate_findings(findings)
    if final_rules_json:
        rules = json.loads(final_rules_json)
        print(f"\n{'='*60}\n 📋 CONSOLIDATED RULES\n{'='*60}\n{json.dumps(rules, indent=2)}")
        out_file = pdf_path.with_suffix('.vision.rules.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2)
        logger.info(f"   ✅ Rules saved to: {out_file.name}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    analyze_with_vision(Path(sys.argv[1]))
