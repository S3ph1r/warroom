"""
IDP Pipeline - Module C: Extraction Engine (Google AI Version)
Uses Google Gemini for high-quality code generation.
Falls back to Ollama if Google quota is exceeded.
"""
import os
import sys
import json
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import unified LLM wrapper (same as Council)
from intelligence.llm_wrapper import LLMWrapper

# Import local modules
from ingestion.pipeline.parser_registry import ParserRegistry, compute_fingerprint
from ingestion.pipeline.router import DocumentType
from ingestion.prompts.code_generation import (
    PROMPT_CSV_HOLDINGS,
    PROMPT_CSV_TRANSACTIONS,
    PROMPT_PDF_HOLDINGS,
    PROMPT_PDF_TRANSACTIONS,
    PROMPT_FIX_ERROR
)


def get_extended_sample(file_path: Path, max_lines: int = 50) -> str:
    """Get extended sample for code generation."""
    ext = file_path.suffix.lower()
    
    if ext == '.csv':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip())
                return '\n'.join(lines)
        except:
            return ""
    
    elif ext == '.pdf':
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                # Get several pages to understand the format
                for i, page in enumerate(pdf.pages[:5]):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {i+1} ---\n{text}")
            return '\n'.join(text_parts)
        except:
            return ""
    
    return ""


def extract_code_from_response(response: str) -> Optional[str]:
    """Extract Python code block from LLM response."""
    if not response:
        return None
        
    # Find code block
    if "```python" in response:
        start = response.find("```python") + 9
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    
    # Check if it starts with import
    if response.strip().startswith("import ") or response.strip().startswith("def "):
        return response.strip()
    
    return None


def validate_parser_code(code: str) -> tuple[bool, str]:
    """Validate that parser code is syntactically correct."""
    if not code:
        return False, "Empty code"
        
    try:
        compile(code, '<string>', 'exec')
        
        if 'def parse(' not in code:
            return False, "Missing 'def parse(' function"
        
        return True, "ok"
        
    except SyntaxError as e:
        return False, f"Syntax error: {e}"


def execute_parser(code: str, file_path: Path) -> tuple[bool, Any, str]:
    """Execute parser code in isolated namespace."""
    try:
        namespace = {}
        exec(code, namespace)
        
        parse_func = namespace.get('parse')
        if not parse_func:
            return False, None, "parse() function not found"
        
        result = parse_func(str(file_path))
        
        if not isinstance(result, list):
            return False, None, f"Expected list, got {type(result)}"
        
        if len(result) == 0:
            return False, result, "Parser returned empty list"
        
        return True, result, ""
        
    except Exception as e:
        tb = traceback.format_exc()
        return False, None, f"{str(e)}\n{tb}"


class ExtractionEngine:
    """
    The Extraction Engine - generates and executes parsers using Google AI.
    
    Strategy:
    1. Try to use cached parser from registry
    2. If not found, generate new parser with Google AI (Gemini)
    3. If Google fails or quota exceeded, fallback to Ollama
    4. Implement self-correction loop on errors
    """
    
    def __init__(self, max_retries: int = 2, prefer_google: bool = True):
        self.registry = ParserRegistry()
        self.max_retries = max_retries
        self.prefer_google = prefer_google
        
        # Initialize LLM providers
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # Primary: Google Gemini (same as Council)
        self.google_llm = None
        if self.google_api_key:
            try:
                self.google_llm = LLMWrapper(
                    provider="google",
                    api_key=self.google_api_key,
                    model="gemini-2.5-flash"  # Same model as Council
                )
                logger.info("✅ Google AI (Gemini) initialized for parser generation")
            except Exception as e:
                logger.warning(f"Google AI init failed: {e}")
        
        # Fallback: Ollama
        self.ollama_llm = LLMWrapper(
            provider="ollama",
            model=os.getenv("OLLAMA_CODER_MODEL", "qwen2.5:14b-instruct-q6_K")
        )
        logger.info("✅ Ollama fallback initialized")
        
        self.stats = {
            'extractions': 0,
            'cache_hits': 0,
            'google_generations': 0,
            'ollama_generations': 0,
            'failures': 0
        }
    
    def _call_llm(self, prompt: str, use_google: bool = True) -> Optional[str]:
        """Call LLM for code generation."""
        messages = [
            {"role": "system", "content": "Sei un Senior Python Developer specializzato in data parsing. Genera codice Python pulito e funzionante. Restituisci SOLO il codice, senza spiegazioni."},
            {"role": "user", "content": prompt}
        ]
        
        # Try Google first if preferred and available
        if use_google and self.google_llm and self.prefer_google:
            try:
                response = self.google_llm.chat(messages, json_mode=False)
                # Only reject if response starts with "Error:" (actual error from LLM wrapper)
                if response and not response.strip().startswith("Error:"):
                    self.stats['google_generations'] += 1
                    logger.info("   🌐 Generated with Google AI")
                    return response
                else:
                    logger.warning(f"   ⚠️ Google AI error: {response[:100] if response else 'None'}")
            except Exception as e:
                logger.warning(f"   ⚠️ Google AI failed: {e}")
        
        # Fallback to Ollama
        try:
            response = self.ollama_llm.chat(messages, json_mode=False)
            if response:
                self.stats['ollama_generations'] += 1
                logger.info("   🦙 Generated with Ollama")
                return response
        except Exception as e:
            logger.error(f"   ❌ Ollama failed: {e}")
        
        return None
    
    def extract(self, file_path: Path, broker: str, doc_type: DocumentType) -> List[Dict]:
        """
        Extract data from file using cached or generated parser.
        """
        self.stats['extractions'] += 1
        logger.info(f"⚙️ Extracting: {file_path.name} | Broker: {broker} | Type: {doc_type.value}")
        
        # Hybrid/Dynamic Parser Routing
        if file_path.suffix.lower() == '.csv':
            try:
                from ingestion.pipeline.hybrid_csv_parser import parse_holdings_hybrid
                logger.info("   🔍 Using Hybrid CSV Parser (Sniffer + Ollama)...")
                result = parse_holdings_hybrid(str(file_path))
                if result:
                    self.stats['extractions'] += 1
                    logger.info(f"   ✅ Extracted {len(result)} records via Hybrid Parser")
                    return result
            except Exception as e:
                logger.error(f"   ❌ Hybrid CSV parser failed: {e}")

        elif file_path.suffix.lower() == '.pdf':
            try:
                from ingestion.pipeline.dynamic_pdf_parser import DynamicPDFParser
                logger.info("   🔍 Using Dynamic PDF Parser (Blind Analyst + Regex Miner)...")
                parser = DynamicPDFParser()
                # Initialize rules discovery only if not cached (can be optimized later)
                # For now, re-discover per file to be safe and robust
                result = parser.parse(str(file_path))
                if result:
                    self.stats['extractions'] += 1
                    logger.info(f"   ✅ Extracted {len(result)} records via Dynamic Parser")
                    return result
            except Exception as e:
                 logger.error(f"   ❌ Dynamic PDF parser failed: {e}")

        # Legacy/Fallback Logic (Registry & Generation)
        # 1. Compute fingerprint
        fingerprint = compute_fingerprint(file_path)
        logger.info(f"   Fingerprint: {fingerprint}")
        
        # 2. Check registry for cached parser
        cached_code = self.registry.get(broker, doc_type.value, fingerprint)
        
        if cached_code:
            self.stats['cache_hits'] += 1
            logger.info(f"   📦 Using cached parser")
            
            success, result, error = execute_parser(cached_code, file_path)
            
            if success:
                self.registry.record_success(broker, doc_type.value, fingerprint)
                logger.info(f"   ✅ Extracted {len(result)} records")
                return result
            else:
                logger.warning(f"   ⚠️ Cached parser failed: {error[:100]}")
                self.registry.record_error(broker, doc_type.value, fingerprint, error)
        
        # 3. Generate new parser
        logger.info(f"   🧠 Generating new parser...")
        
        code = self._generate_parser(file_path, doc_type)
        
        if not code:
            self.stats['failures'] += 1
            logger.error(f"   ❌ Code generation failed")
            return []
        
        # 4. Validate
        valid, validation_msg = validate_parser_code(code)
        
        if not valid:
            logger.error(f"   ❌ Generated code invalid: {validation_msg}")
            self.stats['failures'] += 1
            return []
        
        # 5. Execute with retry loop
        for attempt in range(self.max_retries + 1):
            success, result, error = execute_parser(code, file_path)
            
            if success and len(result) > 0:
                # Validate extracted data has required fields
                sample = result[0]
                if doc_type == DocumentType.TRANSACTIONS:
                    has_ticker = sample.get('ticker') and sample.get('ticker') != 'UNKNOWN'
                    if not has_ticker:
                        logger.warning(f"   ⚠️ Parser didn't extract ticker properly, trying to fix...")
                        code = self._fix_parser(code, "Il campo 'ticker' è vuoto o UNKNOWN. Devi estrarre il nome/simbolo del titolo dalle righe della transazione.")
                        if code:
                            continue
                
                # Save to registry
                self.registry.save(broker, doc_type.value, fingerprint, code)
                logger.info(f"   ✅ Extracted {len(result)} records (attempt {attempt + 1})")
                return result
            
            if attempt < self.max_retries:
                logger.warning(f"   ⚠️ Attempt {attempt + 1} failed, trying self-correction...")
                code = self._fix_parser(code, error)
                if not code:
                    break
        
        self.stats['failures'] += 1
        logger.error(f"   ❌ Extraction failed after {self.max_retries + 1} attempts")
        return []
    
    def _generate_parser(self, file_path: Path, doc_type: DocumentType) -> Optional[str]:
        """Generate parser code using LLM."""
        ext = file_path.suffix.lower()
        
        # Get sample content
        sample = get_extended_sample(file_path)
        
        if not sample:
            logger.error("   ❌ Could not extract sample from file")
            return None
        
        # Select appropriate prompt
        if ext == '.csv':
            if doc_type == DocumentType.HOLDINGS:
                prompt = PROMPT_CSV_HOLDINGS.format(sample_content=sample)
            else:
                prompt = PROMPT_CSV_TRANSACTIONS.format(sample_content=sample)
        else:  # PDF
            if doc_type == DocumentType.HOLDINGS:
                prompt = PROMPT_PDF_HOLDINGS.format(sample_content=sample)
            else:
                prompt = PROMPT_PDF_TRANSACTIONS.format(sample_content=sample)
        
        # Call LLM
        response = self._call_llm(prompt, use_google=True)
        
        if not response:
            return None
        
        # Extract code
        code = extract_code_from_response(response)
        return code
    
    def _fix_parser(self, original_code: str, error: str) -> Optional[str]:
        """Try to fix parser using self-correction loop."""
        prompt = PROMPT_FIX_ERROR.format(
            original_code=original_code,
            error_message=error.split('\n')[0] if error else "Unknown error",
            traceback=error
        )
        
        # Use Google for fixes (more reasoning capability)
        response = self._call_llm(prompt, use_google=True)
        
        if not response:
            return None
        
        code = extract_code_from_response(response)
        
        if code:
            valid, _ = validate_parser_code(code)
            return code if valid else None
        
        return None
    
    def get_stats(self) -> dict:
        """Return extraction statistics."""
        return self.stats.copy()
