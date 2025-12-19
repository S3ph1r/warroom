"""
WAR ROOM - Ingestion Package
"""
from ingestion.parsers import (
    BGSaxoPositionsParser,
    parse_bgsaxo_positions,
    PDF_PARSING_AVAILABLE,
)

if PDF_PARSING_AVAILABLE:
    from ingestion.parsers import BGSaxoTransactionsParser, parse_bgsaxo_transactions

__all__ = [
    'BGSaxoPositionsParser',
    'parse_bgsaxo_positions',
    'PDF_PARSING_AVAILABLE',
]

if PDF_PARSING_AVAILABLE:
    __all__.extend(['BGSaxoTransactionsParser', 'parse_bgsaxo_transactions'])
