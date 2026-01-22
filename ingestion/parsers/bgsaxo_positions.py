"""
WAR ROOM - BG Saxo Positions CSV Parser
Parses positions export from BG Saxo platform
"""
import pandas as pd
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from pathlib import Path
import re
from loguru import logger


class BGSaxoPositionsParser:
    """
    Parser for BG Saxo positions CSV export.
    
    BG Saxo exports positions with columns like:
    - Strumento, Ticker, ISIN, Quantità, Prezzo di apertura, Prz. corrente
    - P&L netto EUR, Valuta, Data/ora apertura, Categoria attività
    """
    
    # Column mapping from Italian BG Saxo to internal format
    COLUMN_MAP = {
        'Strumento': 'name',
        'Ticker': 'ticker_raw',
        'ISIN': 'isin',
        'Quantità': 'quantity',
        'Prezzo di apertura': 'open_price',
        'Prz. corrente': 'current_price',
        'P&L netto EUR': 'pnl_eur',
        'Valuta': 'currency',
        'Data/ora apertura': 'open_datetime',
        'Valore di mercato (EUR)': 'market_value_eur',
        'Valore originale (EUR)': 'original_value_eur',
        'Categoria attività': 'asset_category',
        'Tipo attività': 'asset_type',
        'Long/Short': 'position_type',
        'Conto': 'account',
    }
    
    # Asset class mapping
    ASSET_CLASS_MAP = {
        'Azione': 'STOCK',
        'Exchange Traded Fund (ETF)': 'ETF',
        'Obbligazione': 'BOND',
        'Opzione': 'OPTION',
        'Crypto': 'CRYPTO',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.df_raw = None
        self.df_parsed = None
        
    def parse(self) -> pd.DataFrame:
        """
        Parse the BG Saxo positions CSV file.
        
        Returns:
            DataFrame with standardized columns
        """
        import csv
        
        logger.info(f"Parsing BG Saxo positions from: {self.file_path}")
        
        # Read CSV using csv module for proper quote handling
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # First row is header
        header = rows[0]
        logger.debug(f"Found {len(header)} columns in header")
        
        # Create mapping from column name to index
        col_idx = {name: i for i, name in enumerate(header)}
        
        # Parse data rows (skip header, skip rows with wrong column count)
        parsed_rows = []
        for row_num, row in enumerate(rows[1:], start=2):
            # Skip rows that don't match header column count (summary rows)
            if len(row) != len(header):
                logger.debug(f"Skipping row {row_num}: column count mismatch ({len(row)} vs {len(header)})")
                continue
            
            parsed_row = self._parse_row_from_list(row, col_idx)
            if parsed_row:
                parsed_rows.append(parsed_row)
        
        self.df_parsed = pd.DataFrame(parsed_rows)
        
        logger.info(f"Successfully parsed {len(self.df_parsed)} positions")
        return self.df_parsed
    
    def _parse_row_from_list(self, row: list, col_idx: dict) -> Optional[Dict]:
        """Parse a single row from list format using column index mapping"""
        try:
            # Get ticker
            ticker_raw = row[col_idx.get('Ticker', 0)].strip() if col_idx.get('Ticker') else ''
            ticker = self._clean_ticker(ticker_raw)
            
            if not ticker or ':' not in ticker_raw:
                return None
            
            # Parse values using column index
            quantity = self._parse_number(row[col_idx.get('Quantità', 0)])
            open_price = self._parse_number(row[col_idx.get('Prezzo di apertura', 0)])
            current_price = self._parse_number(row[col_idx.get('Prz. corrente', 0)])
            pnl_eur = self._parse_number(row[col_idx.get('P&L netto EUR', 0)])
            market_value_eur = self._parse_number(row[col_idx.get('Valore di mercato (EUR)', 0)])
            original_value_eur = self._parse_number(row[col_idx.get('Valore originale (EUR)', 0)])
            
            # Get string values
            name = row[col_idx.get('Strumento', 0)].strip()
            currency = row[col_idx.get('Valuta', 0)].strip() or 'EUR'
            isin = row[col_idx.get('ISIN', 0)].strip()
            asset_type = row[col_idx.get('Tipo attività', 0)].strip() if col_idx.get('Tipo attività') else 'Azione'
            
            # Parse datetime
            open_datetime_str = row[col_idx.get('Data/ora apertura', 0)] if col_idx.get('Data/ora apertura') else ''
            open_datetime = self._parse_datetime(open_datetime_str)
            
            # Determine asset class
            asset_class = self.ASSET_CLASS_MAP.get(asset_type, 'STOCK')
            
            # Extract exchange
            exchange = self._extract_exchange(ticker_raw)
            
            return {
                'ticker': ticker,
                'ticker_raw': ticker_raw,
                'name': name,
                'isin': isin if isin and isin != 'nan' else None,
                'quantity': quantity,
                'open_price': open_price,
                'current_price': current_price,
                'pnl_eur': pnl_eur,
                'market_value_eur': market_value_eur,
                'original_value_eur': original_value_eur,
                'currency': currency,
                'asset_class': asset_class,
                'exchange': exchange,
                'open_datetime': open_datetime,
                'platform': 'BG_SAXO',
            }
            
        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            return None
    
    def _parse_row(self, row: pd.Series) -> Optional[Dict]:
        """Parse a single row from the CSV"""
        try:
            # Extract ticker symbol (format: "NVDA:xnas" -> "NVDA")
            ticker_raw = str(row.get('Ticker', '')).strip()
            ticker = self._clean_ticker(ticker_raw)
            
            if not ticker:
                return None
            
            # Parse quantity (handle European number format)
            quantity = self._parse_number(row.get('Quantità', 0))
            
            # Parse prices
            open_price = self._parse_number(row.get('Prezzo di apertura', 0))
            current_price = self._parse_number(row.get('Prz. corrente', 0))
            
            # Parse P&L
            pnl_eur = self._parse_number(row.get('P&L netto EUR', 0))
            market_value_eur = self._parse_number(row.get('Valore di mercato (EUR)', 0))
            original_value_eur = self._parse_number(row.get('Valore originale (EUR)', 0))
            
            # Parse datetime
            open_datetime = self._parse_datetime(row.get('Data/ora apertura', ''))
            
            # Determine asset class
            asset_type = str(row.get('Tipo attività', 'Azione')).strip()
            asset_class = self.ASSET_CLASS_MAP.get(asset_type, 'STOCK')
            
            # Get currency
            currency = str(row.get('Valuta', 'EUR')).strip()
            
            # Get ISIN
            isin = str(row.get('ISIN', '')).strip()
            
            # Get name
            name = str(row.get('Strumento', '')).strip()
            
            # Extract exchange from ticker (NVDA:xnas -> xnas -> NASDAQ)
            exchange = self._extract_exchange(ticker_raw)
            
            return {
                'ticker': ticker,
                'ticker_raw': ticker_raw,
                'name': name,
                'isin': isin if isin and isin != 'nan' else None,
                'quantity': quantity,
                'open_price': open_price,
                'current_price': current_price,
                'pnl_eur': pnl_eur,
                'market_value_eur': market_value_eur,
                'original_value_eur': original_value_eur,
                'currency': currency,
                'asset_class': asset_class,
                'exchange': exchange,
                'open_datetime': open_datetime,
                'platform': 'BG_SAXO',
            }
            
        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            return None
    
    def _clean_ticker(self, ticker_raw: str) -> str:
        """
        Clean ticker symbol from BG Saxo format.
        Examples:
            - "NVDA:xnas" -> "NVDA"
            - "02050:xhkg" -> "02050.HK"
            - "SWDA:xmil" -> "SWDA.MI"
        """
        if not ticker_raw or ticker_raw == 'nan':
            return ''
        
        parts = ticker_raw.split(':')
        if len(parts) >= 1:
            return parts[0].strip()
        return ticker_raw.strip()
    
    def _extract_exchange(self, ticker_raw: str) -> str:
        """Extract exchange code from raw ticker"""
        exchange_map = {
            'xnas': 'NASDAQ',
            'xnys': 'NYSE',
            'xase': 'AMEX',
            'xmil': 'Milan',
            'xetr': 'Frankfurt',
            'xpar': 'Paris',
            'xhkg': 'Hong Kong',
            'xcse': 'Copenhagen',
            'xhel': 'Helsinki',
            'xtsx': 'Toronto',
        }
        
        if ':' in ticker_raw:
            exchange_code = ticker_raw.split(':')[1].lower()
            return exchange_map.get(exchange_code, exchange_code.upper())
        return 'UNKNOWN'
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from European format (comma as decimal, dot as thousands)"""
        if pd.isna(value):
            return Decimal('0')
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        # String parsing
        value_str = str(value).strip()
        
        # Remove currency symbols and whitespace
        value_str = re.sub(r'[€$£\s]', '', value_str)
        
        # Handle European format: 1.234,56 -> 1234.56
        if ',' in value_str and '.' in value_str:
            value_str = value_str.replace('.', '').replace(',', '.')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        # Handle negative with trailing minus or parentheses
        if value_str.endswith('-'):
            value_str = '-' + value_str[:-1]
        
        try:
            return Decimal(value_str)
        except:
            return Decimal('0')
    
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from BG Saxo format: 04-dic-2025 18:50:00"""
        if pd.isna(value) or not value:
            return None
        
        # Italian month mapping
        month_map = {
            'gen': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'mag': '05', 'giu': '06', 'lug': '07', 'ago': '08',
            'set': '09', 'ott': '10', 'nov': '11', 'dic': '12'
        }
        
        try:
            value_str = str(value).strip()
            
            # Replace Italian month with number
            for it_month, num in month_map.items():
                if it_month in value_str.lower():
                    value_str = value_str.lower().replace(it_month, num)
                    break
            
            # Parse: 04-12-2025 18:50:00
            return datetime.strptime(value_str, '%d-%m-%Y %H:%M:%S')
        except Exception as e:
            logger.debug(f"Could not parse datetime '{value}': {e}")
            return None
    
    def get_summary(self) -> Dict:
        """Get summary statistics of parsed positions"""
        if self.df_parsed is None:
            self.parse()
        
        df = self.df_parsed
        
        return {
            'total_positions': len(df),
            'total_market_value_eur': float(df['market_value_eur'].sum()),
            'total_pnl_eur': float(df['pnl_eur'].sum()),
            'by_asset_class': df.groupby('asset_class')['market_value_eur'].sum().to_dict(),
            'currencies': df['currency'].unique().tolist(),
            'exchanges': df['exchange'].unique().tolist(),
        }
    
    def to_asset_registry(self) -> List[Dict]:
        """Convert parsed positions to AssetRegistry format for database"""
        if self.df_parsed is None:
            self.parse()
        
        assets = []
        for _, row in self.df_parsed.iterrows():
            assets.append({
                'ticker': row['ticker'],
                'isin': row['isin'],
                'name': row['name'],
                'asset_class': row['asset_class'],
                'currency': row['currency'],
                'exchange': row['exchange'],
                'watch_level': 1,  # Default: Hold
            })
        
        return assets
    
    def to_transactions(self) -> List[Dict]:
        """
        Convert positions to initial BUY transactions.
        Note: This creates synthetic transactions based on current positions.
        Real transaction history should come from PDF parsing.
        """
        if self.df_parsed is None:
            self.parse()
        
        transactions = []
        for _, row in self.df_parsed.iterrows():
            transactions.append({
                'timestamp': row['open_datetime'] or datetime.now(),
                'ticker_symbol': row['ticker'],
                'isin': row['isin'],
                'platform': 'BG_SAXO',
                'operation_type': 'BUY',
                'quantity': row['quantity'],
                'price_unit': row['open_price'],
                'fiat_amount': row['original_value_eur'],
                'currency_original': row['currency'],
                'status': 'VERIFIED',
                'notes': f"Imported from BG Saxo positions snapshot",
            })
        
        return transactions


def parse_bgsaxo_positions(file_path: str) -> pd.DataFrame:
    """Convenience function to parse BG Saxo positions CSV"""
    parser = BGSaxoPositionsParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    # Test parsing
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/BGSAXO/Posizioni_19-dic-2025_17_49_12.csv"
    
    parser = BGSaxoPositionsParser(file_path)
    df = parser.parse()
    
    print("\n📊 Parsed Positions:")
    print(df[['ticker', 'name', 'quantity', 'current_price', 'pnl_eur', 'asset_class']].to_string())
    
    print("\n📈 Summary:")
    summary = parser.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
