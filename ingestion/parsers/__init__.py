"""
WAR ROOM - Ingestion Parsers Package
"""
from ingestion.parsers.bgsaxo_positions import BGSaxoPositionsParser, parse_bgsaxo_positions

# PDF parser is optional (requires tabula-py + Java)
try:
    from ingestion.parsers.bgsaxo_transactions import BGSaxoTransactionsParser, parse_bgsaxo_transactions
    PDF_PARSING_AVAILABLE = True
except ImportError:
    PDF_PARSING_AVAILABLE = False

__all__ = [
    'BGSaxoPositionsParser',
    'parse_bgsaxo_positions',
    'BGSaxoTransactionsParser',
    'parse_bgsaxo_transactions',
    'PDF_PARSING_AVAILABLE',
]
