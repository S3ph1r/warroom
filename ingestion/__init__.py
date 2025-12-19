"""
WAR ROOM - Ingestion Package
"""
from ingestion.parsers import (
    BGSaxoPositionsParser,
    parse_bgsaxo_positions,
    PDF_PARSING_AVAILABLE,
)

if PDF_PARSING_AVAILABLE:
    from ingestion.parsers import (
        BGSaxoTransactionsPDFParser,
        parse_bgsaxo_transactions_pdf,
        ScalableCapitalPDFParser,
        parse_scalable_pdf,
        parse_all_scalable_pdfs,
        RevolutPDFParser,
        parse_revolut_pdf,
        TradeRepublicPDFParser,
        parse_trade_republic_pdf,
        IBKRCSVParser,
        parse_ibkr_csv,
        BinanceCSVParser,
        parse_binance_csv,
        parse_all_binance_csvs,
    )

__all__ = [
    'BGSaxoPositionsParser',
    'parse_bgsaxo_positions',
    'PDF_PARSING_AVAILABLE',
]

if PDF_PARSING_AVAILABLE:
    __all__.extend([
        'BGSaxoTransactionsPDFParser',
        'parse_bgsaxo_transactions_pdf',
        'ScalableCapitalPDFParser',
        'parse_scalable_pdf',
        'parse_all_scalable_pdfs',
        'RevolutPDFParser',
        'parse_revolut_pdf',
        'TradeRepublicPDFParser',
        'parse_trade_republic_pdf',
        'IBKRCSVParser',
        'parse_ibkr_csv',
        'BinanceCSVParser',
        'parse_binance_csv',
        'parse_all_binance_csvs',
    ])
