"""
WAR ROOM - Ingestion Package
New IDP Pipeline Architecture.

Note: Old parsers in ingestion/parsers/ are deprecated.
Use the new pipeline modules instead:
    from ingestion.pipeline import IDPPipeline
"""

# New IDP Pipeline exports
from ingestion.pipeline.gatekeeper import Gatekeeper, validate_file, get_broker_from_path
from ingestion.pipeline.router import DocumentRouter, DocumentType, ClassificationResult
from ingestion.pipeline.parser_registry import ParserRegistry, compute_fingerprint
from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.data_loader import DataLoader

__all__ = [
    # Pipeline modules
    'Gatekeeper',
    'validate_file',
    'get_broker_from_path',
    'DocumentRouter',
    'DocumentType',
    'ClassificationResult',
    'ParserRegistry',
    'compute_fingerprint',
    'ExtractionEngine',
    'DataLoader',
]

# Legacy compatibility flag
PDF_PARSING_AVAILABLE = True  # pdfplumber is the new standard
