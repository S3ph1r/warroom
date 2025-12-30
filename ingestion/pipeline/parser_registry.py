"""
IDP Pipeline - Parser Registry
Stores and retrieves LLM-generated parsers for reuse.
"""
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Default registry location
REGISTRY_PATH = Path(__file__).parent.parent / "generated_parsers" / "registry.json"


def compute_fingerprint(file_path: Path, sample_size: int = 2000) -> str:
    """
    Compute a layout fingerprint for a file.
    Used to identify if an existing parser can be reused.
    
    For CSV: Hash of header row
    For PDF: Hash of first 2 pages structure
    """
    try:
        ext = file_path.suffix.lower()
        
        if ext == '.csv':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read header and first few lines
                header = f.readline().strip()
                return hashlib.md5(header.encode()).hexdigest()[:12]
        
        elif ext == '.pdf':
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text_sample = ""
                for i, page in enumerate(pdf.pages[:2]):
                    text = page.extract_text() or ""
                    # Get structure markers (headers, table indicators)
                    text_sample += text[:1000]
                return hashlib.md5(text_sample.encode()).hexdigest()[:12]
        
        else:
            # Fallback: hash first N bytes
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read(sample_size)).hexdigest()[:12]
                
    except Exception as e:
        logger.error(f"Fingerprint computation failed: {e}")
        return "unknown"


class ParserRegistry:
    """
    Registry for storing and retrieving LLM-generated parsers.
    
    Key format: {broker}|{doc_type}|{fingerprint}
    Value: {code, created_at, success_count, last_error}
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_PATH
        self.registry = self._load()
    
    def _load(self) -> dict:
        """Load registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
        return {}
    
    def _save(self):
        """Persist registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _make_key(self, broker: str, doc_type: str, fingerprint: str) -> str:
        """Create registry key."""
        return f"{broker}|{doc_type}|{fingerprint}"
    
    def get(self, broker: str, doc_type: str, fingerprint: str) -> Optional[str]:
        """
        Retrieve a cached parser code.
        
        Returns:
            Parser code string if found, None otherwise
        """
        key = self._make_key(broker, doc_type, fingerprint)
        entry = self.registry.get(key)
        
        if entry:
            logger.info(f"📦 Found cached parser: {key}")
            return entry.get('code')
        
        return None
    
    def save(self, broker: str, doc_type: str, fingerprint: str, code: str):
        """
        Save a new parser to the registry.
        """
        key = self._make_key(broker, doc_type, fingerprint)
        
        self.registry[key] = {
            'code': code,
            'created_at': datetime.now().isoformat(),
            'success_count': 0,
            'last_error': None
        }
        
        self._save()
        logger.info(f"💾 Saved new parser: {key}")
    
    def record_success(self, broker: str, doc_type: str, fingerprint: str):
        """Record a successful parse."""
        key = self._make_key(broker, doc_type, fingerprint)
        if key in self.registry:
            self.registry[key]['success_count'] = \
                self.registry[key].get('success_count', 0) + 1
            self._save()
    
    def record_error(self, broker: str, doc_type: str, fingerprint: str, error: str):
        """Record a parse error."""
        key = self._make_key(broker, doc_type, fingerprint)
        if key in self.registry:
            self.registry[key]['last_error'] = {
                'message': error,
                'timestamp': datetime.now().isoformat()
            }
            self._save()
    
    def invalidate(self, broker: str, doc_type: str, fingerprint: str):
        """Remove a parser from registry (e.g., if it keeps failing)."""
        key = self._make_key(broker, doc_type, fingerprint)
        if key in self.registry:
            del self.registry[key]
            self._save()
            logger.info(f"🗑️ Invalidated parser: {key}")
    
    def list_parsers(self) -> list:
        """List all registered parsers with metadata."""
        result = []
        for key, entry in self.registry.items():
            broker, doc_type, fingerprint = key.split('|')
            result.append({
                'broker': broker,
                'doc_type': doc_type,
                'fingerprint': fingerprint,
                'created_at': entry.get('created_at'),
                'success_count': entry.get('success_count', 0),
                'has_error': entry.get('last_error') is not None
            })
        return result
