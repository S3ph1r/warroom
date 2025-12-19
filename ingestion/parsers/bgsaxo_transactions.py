"""
WAR ROOM - BG Saxo Transactions PDF Parser
Parses transaction history from BG Saxo PDF exports
"""
import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from pathlib import Path
import re
from loguru import logger

# Try to import tabula for PDF parsing
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    logger.warning("tabula-py not installed. PDF parsing will not be available.")


class BGSaxoTransactionsParser:
    """
    Parser for BG Saxo transactions PDF export.
    
    BG Saxo exports two types of PDF reports:
    - Trades: Buy/Sell orders
    - Transactions: All account movements (including dividends, fees, etc.)
    """
    
    # Operation type mapping
    OPERATION_MAP = {
        'Acquisto': 'BUY',
        'Vendita': 'SELL',
        'Bought': 'BUY',
        'Sold': 'SELL',
        'Buy': 'BUY',
        'Sell': 'SELL',
        'Dividend': 'DIVIDEND',
        'Dividendo': 'DIVIDEND',
        'Fee': 'FEE',
        'Commissione': 'FEE',
        'Interest': 'INTEREST',
        'Interesse': 'INTEREST',
        'Deposit': 'DEPOSIT',
        'Deposito': 'DEPOSIT',
        'Withdrawal': 'WITHDRAW',
        'Prelievo': 'WITHDRAW',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.tables = None
        self.df_parsed = None
        
        if not TABULA_AVAILABLE:
            raise ImportError(
                "tabula-py is required for PDF parsing. "
                "Install it with: pip install tabula-py\n"
                "Also requires Java to be installed."
            )
    
    def parse(self) -> pd.DataFrame:
        """
        Parse BG Saxo transactions PDF.
        
        Returns:
            DataFrame with standardized transaction columns
        """
        logger.info(f"Parsing BG Saxo transactions from: {self.file_path}")
        
        # Extract all tables from PDF
        self.tables = tabula.read_pdf(
            str(self.file_path),
            pages='all',
            multiple_tables=True,
            encoding='utf-8',
            lattice=True,  # Use lines in PDF to detect table boundaries
        )
        
        logger.info(f"Found {len(self.tables)} tables in PDF")
        
        # Process each table
        all_transactions = []
        for i, table in enumerate(self.tables):
            logger.debug(f"Processing table {i+1} with {len(table)} rows")
            transactions = self._process_table(table)
            all_transactions.extend(transactions)
        
        self.df_parsed = pd.DataFrame(all_transactions)
        
        logger.info(f"Successfully parsed {len(self.df_parsed)} transactions")
        return self.df_parsed
    
    def _process_table(self, df: pd.DataFrame) -> List[Dict]:
        """Process a single table from the PDF"""
        transactions = []
        
        # Try to identify column structure
        columns = df.columns.tolist()
        
        # Look for key columns to determine table type
        has_trade_columns = any(
            'trade' in str(c).lower() or 
            'instrument' in str(c).lower() or 
            'strumento' in str(c).lower()
            for c in columns
        )
        
        if not has_trade_columns:
            # Try using first row as header
            df.columns = df.iloc[0]
            df = df.iloc[1:]
        
        for _, row in df.iterrows():
            transaction = self._parse_row(row)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _parse_row(self, row: pd.Series) -> Optional[Dict]:
        """Parse a single row from a table"""
        try:
            # Convert row to dict for easier access
            row_dict = row.to_dict()
            row_str = ' '.join(str(v) for v in row_dict.values() if pd.notna(v))
            
            # Skip if row seems like a header or empty
            if not row_str or len(row_str) < 10:
                return None
            
            # Skip summary rows
            if any(term in row_str.lower() for term in ['total', 'totale', 'summary', 'riepilogo']):
                return None
            
            # Try to extract data from row
            # This is a simplified parser - may need adjustment based on actual PDF structure
            
            # Look for operation type
            operation_type = None
            for key, value in self.OPERATION_MAP.items():
                if key.lower() in row_str.lower():
                    operation_type = value
                    break
            
            if not operation_type:
                return None
            
            # Extract ticker (usually in format like "NVDA", "AAPL", etc.)
            ticker_match = re.search(r'\b([A-Z]{1,5})\b', row_str)
            ticker = ticker_match.group(1) if ticker_match else None
            
            # Extract ISIN if present
            isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', row_str)
            isin = isin_match.group(1) if isin_match else None
            
            # Extract numbers (quantity, price, amount)
            numbers = re.findall(r'[\d.,]+', row_str)
            numbers = [self._parse_number(n) for n in numbers if self._parse_number(n) > 0]
            
            # Extract date
            date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', row_str)
            timestamp = None
            if date_match:
                timestamp = self._parse_date(date_match.group(1))
            
            # Build transaction dict
            return {
                'timestamp': timestamp or datetime.now(),
                'ticker_symbol': ticker,
                'isin': isin,
                'platform': 'BG_SAXO',
                'operation_type': operation_type,
                'quantity': numbers[0] if len(numbers) > 0 else Decimal('0'),
                'price_unit': numbers[1] if len(numbers) > 1 else Decimal('0'),
                'fiat_amount': numbers[-1] if numbers else Decimal('0'),
                'currency_original': 'EUR',  # Default, may need parsing
                'status': 'VERIFIED',
                'notes': f"Imported from PDF: {self.file_path.name}",
                'csv_source': self.file_path.name,
            }
            
        except Exception as e:
            logger.debug(f"Could not parse row: {e}")
            return None
    
    def _parse_number(self, value) -> Decimal:
        """Parse number handling European format"""
        if pd.isna(value):
            return Decimal('0')
        
        value_str = str(value).strip()
        value_str = re.sub(r'[€$£\s]', '', value_str)
        
        # Handle European format
        if ',' in value_str and '.' in value_str:
            # 1.234,56 -> 1234.56
            value_str = value_str.replace('.', '').replace(',', '.')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        try:
            return Decimal(value_str)
        except:
            return Decimal('0')
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats"""
        formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d/%m/%y',
            '%d-%m-%y',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None
    
    def get_summary(self) -> Dict:
        """Get summary of parsed transactions"""
        if self.df_parsed is None or len(self.df_parsed) == 0:
            return {'total_transactions': 0}
        
        df = self.df_parsed
        
        return {
            'total_transactions': len(df),
            'by_operation': df['operation_type'].value_counts().to_dict() if 'operation_type' in df.columns else {},
            'date_range': {
                'from': df['timestamp'].min() if 'timestamp' in df.columns else None,
                'to': df['timestamp'].max() if 'timestamp' in df.columns else None,
            }
        }


def parse_bgsaxo_transactions(file_path: str) -> pd.DataFrame:
    """Convenience function to parse BG Saxo transactions PDF"""
    parser = BGSaxoTransactionsParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/BGSAXO/Transactions_19807401_2025-01-01_2025-12-19.pdf"
    
    try:
        parser = BGSaxoTransactionsParser(file_path)
        df = parser.parse()
        
        print("\n📊 Parsed Transactions:")
        print(df.to_string())
        
        print("\n📈 Summary:")
        summary = parser.get_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
    except ImportError as e:
        print(f"❌ {e}")
