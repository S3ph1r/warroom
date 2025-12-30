"""
IDP Pipeline - Module B: Router
Document classification using LLM to identify HOLDINGS vs TRANSACTIONS.
"""
import os
import json
import requests
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Ollama configuration (WSL)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct-q6_K")


class DocumentType(str, Enum):
    HOLDINGS = "HOLDINGS"
    TRANSACTIONS = "TRANSACTIONS"
    TRASH = "TRASH"


@dataclass
class ClassificationResult:
    category: DocumentType
    confidence: float
    reasoning: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ClassificationResult':
        return cls(
            category=DocumentType(data.get('category', 'TRASH').upper()),
            confidence=float(data.get('confidence', 0.0)),
            reasoning=data.get('reasoning', '')
        )
    
    def is_valid(self, min_confidence: float = 0.7) -> bool:
        """Check if classification is valid (not TRASH and confident)."""
        return self.category != DocumentType.TRASH and self.confidence >= min_confidence


# Classification prompt following IDP document spec
CLASSIFICATION_PROMPT = """Sei un assistente automatico di back-office finanziario. Il tuo compito è classificare il documento in base al testo fornito.

Le categorie possibili sono ESCLUSIVAMENTE:
1. `HOLDINGS`: Il documento è un report statico di portafoglio (elenco titoli posseduti in una data). Parole chiave tipiche: 'Posizioni', 'Quantità', 'Valore Mercato', 'Asset Allocation', 'Portfolio', 'Financial Status'.
2. `TRANSACTIONS`: Il documento è un registro cronologico di movimenti (acquisti, vendite, cedole). Parole chiave tipiche: 'Data', 'Time', 'Buy', 'Sell', 'Acquista', 'Vendi', 'Commissione', 'Fee', 'Dividend'.
3. `TRASH`: Il documento non contiene dati utili (es. informative legali, copertine vuote, privacy policy, report fiscali non elaborabili).

TESTO DOCUMENTO:
{content}

Rispondi SOLO con questo JSON (nessun testo aggiuntivo):
{{"category": "HOLDINGS|TRANSACTIONS|TRASH", "confidence": 0.0-1.0, "reasoning": "breve motivo"}}"""


def extract_preview_csv(file_path: Path, max_rows: int = 30) -> str:
    """Extract first N rows from CSV as preview text."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                lines.append(line.rstrip())
            return '\n'.join(lines)
    except Exception as e:
        logger.error(f"CSV preview extraction failed: {e}")
        return ""


def extract_preview_pdf(file_path: Path, max_pages: int = 2) -> str:
    """Extract first N pages from PDF as preview text."""
    try:
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
        
        return '\n'.join(text_parts)
        
    except ImportError:
        logger.error("pdfplumber not installed")
        return ""
    except Exception as e:
        logger.error(f"PDF preview extraction failed: {e}")
        return ""


def extract_preview(file_path: Path) -> str:
    """Extract preview text from file based on extension."""
    ext = file_path.suffix.lower()
    
    if ext == '.csv':
        return extract_preview_csv(file_path)
    elif ext == '.pdf':
        return extract_preview_pdf(file_path)
    elif ext in ['.xls', '.xlsx']:
        return extract_preview_excel(file_path)
    else:
        return ""


def extract_preview_excel(file_path: Path, max_rows: int = 30) -> str:
    """Extract first N rows from Excel as preview text."""
    try:
        import pandas as pd
        
        df = pd.read_excel(file_path, nrows=max_rows)
        return df.to_string()
        
    except Exception as e:
        logger.error(f"Excel preview extraction failed: {e}")
        return ""


def call_ollama(prompt: str, timeout: int = 120) -> Optional[str]:
    """Call Ollama API for classification."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            logger.error(f"Ollama error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        return None
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None


def parse_classification_response(response_text: str) -> Optional[ClassificationResult]:
    """Parse JSON response from LLM."""
    try:
        # Find JSON in response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            data = json.loads(json_str)
            return ClassificationResult.from_dict(data)
        
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
        return None


class DocumentRouter:
    """
    The Router class - classifies documents using LLM.
    """
    
    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        self.stats = {
            'classified': 0,
            'holdings': 0,
            'transactions': 0,
            'trash': 0,
            'failed': 0
        }
    
    def classify(self, file_path: Path) -> ClassificationResult:
        """
        Classify a document by extracting preview and calling LLM.
        
        Returns:
            ClassificationResult with category, confidence, and reasoning
        """
        logger.info(f"🔍 Classifying: {file_path.name}")
        
        # Extract preview
        preview = extract_preview(file_path)
        
        if not preview:
            logger.warning(f"   No preview extracted, defaulting to TRASH")
            return ClassificationResult(
                category=DocumentType.TRASH,
                confidence=0.0,
                reasoning="Failed to extract preview text"
            )
        
        # Truncate if too long (keep context manageable)
        max_chars = 8000
        if len(preview) > max_chars:
            preview = preview[:max_chars] + "\n...[TRUNCATED]..."
        
        # Build prompt
        prompt = CLASSIFICATION_PROMPT.format(content=preview)
        
        # Call LLM
        response = call_ollama(prompt)
        
        if not response:
            logger.warning(f"   LLM call failed, defaulting to TRASH")
            self.stats['failed'] += 1
            return ClassificationResult(
                category=DocumentType.TRASH,
                confidence=0.0,
                reasoning="LLM classification failed"
            )
        
        # Parse response
        result = parse_classification_response(response)
        
        if not result:
            logger.warning(f"   Failed to parse response, defaulting to TRASH")
            self.stats['failed'] += 1
            return ClassificationResult(
                category=DocumentType.TRASH,
                confidence=0.0,
                reasoning="Failed to parse LLM response"
            )
        
        # Update stats
        self.stats['classified'] += 1
        if result.category == DocumentType.HOLDINGS:
            self.stats['holdings'] += 1
        elif result.category == DocumentType.TRANSACTIONS:
            self.stats['transactions'] += 1
        else:
            self.stats['trash'] += 1
        
        logger.info(f"   -> {result.category.value} (confidence: {result.confidence:.2f})")
        logger.info(f"   Reason: {result.reasoning}")
        
        return result
    
    def get_stats(self) -> dict:
        """Return classification statistics."""
        return self.stats.copy()
