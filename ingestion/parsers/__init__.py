"""
WAR ROOM - Ingestion Parsers Package
"""
from ingestion.parsers.bgsaxo_positions import BGSaxoPositionsParser, parse_bgsaxo_positions

# PDF parsers (require PyMuPDF)
try:
    from ingestion.parsers.bgsaxo_transactions import BGSaxoTransactionsPDFParser, parse_bgsaxo_transactions_pdf
    from ingestion.parsers.scalable_capital import ScalableCapitalPDFParser, parse_scalable_pdf, parse_all_scalable_pdfs
    from ingestion.parsers.revolut import RevolutPDFParser, parse_revolut_pdf
    from ingestion.parsers.traderepublic import TradeRepublicPDFParser, parse_trade_republic_pdf
    from ingestion.parsers.ibkr import IBKRCSVParser, parse_ibkr_csv
    from ingestion.parsers.binance import BinanceCSVParser, parse_binance_csv, parse_all_binance_csvs
    PDF_PARSING_AVAILABLE = True
except ImportError:
    PDF_PARSING_AVAILABLE = False

__all__ = [
    'BGSaxoPositionsParser',
    'parse_bgsaxo_positions',
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
    'PDF_PARSING_AVAILABLE',
]
