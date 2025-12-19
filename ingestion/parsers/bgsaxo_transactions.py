"""
WAR ROOM - BG Saxo Transactions PDF Parser (PyMuPDF version)
Parses transaction history from BG Saxo PDF exports using PyMuPDF
"""
import fitz  # PyMuPDF
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict
from pathlib import Path
from loguru import logger


class BGSaxoTransactionsPDFParser:
    """
    Parser for BG Saxo transactions PDF export using PyMuPDF.
    
    BG Saxo transaction PDFs contain:
    - Cover page (skip)
    - Transaction pages with: Date, Type, Product Name, Operation, Amount, ISIN
    """
    
    # Italian month mapping
    MONTH_MAP = {
        'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8,
        'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
    }
    
    # Operation type patterns
    OPERATION_PATTERNS = {
        r'Acquista\s+(\d+(?:,\d+)?)\s*@\s*([\d.,]+)': 'BUY',
        r'Vendi?\s+(\d+(?:,\d+)?)\s*@\s*([\d.,]+)': 'SELL',
        r'Vendita\s+(\d+(?:,\d+)?)\s*@\s*([\d.,]+)': 'SELL',
        r'Acquis\.\s+(\d+(?:,\d+)?)\s*@\s*([\d.,]+)': 'BUY',
    }
    
    # Transaction types to track
    TRANSACTION_TYPES = {
        'Contrattazione': 'TRADE',
        'Deposito': 'DEPOSIT',
        'Prelievo': 'WITHDRAW',
        'Trasferimento': 'TRANSFER',
        'Dividendo': 'DIVIDEND',
        'Interesse': 'INTEREST',
        'Commissione': 'FEE',
        'Corporate Action': 'CORPORATE_ACTION',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = None
        self.transactions = []
        
    def parse(self) -> List[Dict]:
        """
        Parse all transactions from the PDF.
        
        Returns:
            List of transaction dictionaries
        """
        logger.info(f"Parsing BG Saxo transactions from: {self.file_path}")
        
        self.doc = fitz.open(str(self.file_path))
        total_pages = len(self.doc)
        logger.info(f"PDF has {total_pages} pages")
        
        self.transactions = []
        current_date = None
        
        # Skip first page (cover), parse rest
        for page_num in range(1, total_pages):
            page = self.doc[page_num]
            text = page.get_text()
            
            # Parse transactions from page text
            page_transactions = self._parse_page(text, current_date)
            
            # Update current date from last transaction
            if page_transactions:
                last_tx = page_transactions[-1]
                if last_tx.get('timestamp'):
                    current_date = last_tx['timestamp']
            
            self.transactions.extend(page_transactions)
            
            if (page_num + 1) % 20 == 0:
                logger.info(f"Processed {page_num + 1}/{total_pages} pages, found {len(self.transactions)} transactions")
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_page(self, text: str, last_date: datetime = None) -> List[Dict]:
        """Parse transactions from a single page's text"""
        transactions = []
        lines = text.split('\n')
        
        current_date = last_date
        current_tx = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Try to parse date (format: 19-dic-2025)
            date_match = re.match(r'^(\d{1,2})-([a-z]{3})-(\d{4})$', line.lower())
            if date_match:
                day, month_str, year = date_match.groups()
                month = self.MONTH_MAP.get(month_str, 1)
                try:
                    current_date = datetime(int(year), month, int(day))
                except:
                    pass
                i += 1
                continue
            
            # Check for transaction type
            tx_type = None
            for type_name, type_code in self.TRANSACTION_TYPES.items():
                if line.startswith(type_name):
                    tx_type = type_code
                    break
            
            if tx_type == 'TRADE' and i + 1 < len(lines):
                # Next line should be product name
                product_name = lines[i + 1].strip() if i + 1 < len(lines) else ''
                
                # Look for operation pattern in next lines
                operation_type = None
                quantity = None
                price = None
                amount = None
                isin = None
                
                for j in range(i + 2, min(i + 15, len(lines))):
                    check_line = lines[j].strip()
                    
                    # Try operation patterns
                    for pattern, op_type in self.OPERATION_PATTERNS.items():
                        op_match = re.search(pattern, check_line, re.IGNORECASE)
                        if op_match:
                            operation_type = op_type
                            qty_str = op_match.group(1).replace(',', '.')
                            price_str = op_match.group(2).replace(',', '.')
                            quantity = self._parse_number(qty_str)
                            price = self._parse_number(price_str)
                            break
                    
                    # Look for ISIN
                    isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', check_line)
                    if isin_match:
                        isin = isin_match.group(1)
                    
                    # Look for amount (negative number after product line)
                    amount_match = re.match(r'^-?([\d.,]+)$', check_line)
                    if amount_match and not amount:
                        amount = self._parse_number(check_line)
                
                if product_name and operation_type:
                    transactions.append({
                        'timestamp': current_date,
                        'product_name': product_name,
                        'operation_type': operation_type,
                        'quantity': quantity or Decimal('0'),
                        'price_unit': price or Decimal('0'),
                        'fiat_amount': amount or Decimal('0'),
                        'isin': isin,
                        'platform': 'BG_SAXO',
                        'status': 'VERIFIED',
                    })
            
            elif tx_type == 'DEPOSIT':
                # Look for amount
                for j in range(i + 1, min(i + 5, len(lines))):
                    check_line = lines[j].strip()
                    amount_match = re.match(r'^([\d.,]+)$', check_line)
                    if amount_match:
                        amount = self._parse_number(check_line)
                        transactions.append({
                            'timestamp': current_date,
                            'product_name': 'Cash Deposit',
                            'operation_type': 'DEPOSIT',
                            'quantity': Decimal('1'),
                            'price_unit': amount,
                            'fiat_amount': amount,
                            'isin': None,
                            'platform': 'BG_SAXO',
                            'status': 'VERIFIED',
                        })
                        break
            
            i += 1
        
        return transactions
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from European format"""
        if not value:
            return Decimal('0')
        
        value_str = str(value).strip()
        
        # Remove currency symbols
        value_str = re.sub(r'[€$£\s]', '', value_str)
        
        # Handle European format: 1.234,56 -> 1234.56
        if ',' in value_str and '.' in value_str:
            value_str = value_str.replace('.', '').replace(',', '.')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        # Handle negative
        if value_str.startswith('-'):
            sign = -1
            value_str = value_str[1:]
        else:
            sign = 1
        
        try:
            return Decimal(value_str) * sign
        except InvalidOperation:
            return Decimal('0')
    
    def get_summary(self) -> Dict:
        """Get summary of parsed transactions"""
        if not self.transactions:
            return {'total_transactions': 0}
        
        by_type = {}
        total_deposits = Decimal('0')
        total_buys = Decimal('0')
        total_sells = Decimal('0')
        
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
            
            if op == 'DEPOSIT':
                total_deposits += tx.get('fiat_amount', Decimal('0'))
            elif op == 'BUY':
                total_buys += abs(tx.get('fiat_amount', Decimal('0')))
            elif op == 'SELL':
                total_sells += abs(tx.get('fiat_amount', Decimal('0')))
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'total_deposits': float(total_deposits),
            'total_buys': float(total_buys),
            'total_sells': float(total_sells),
            'date_range': {
                'from': min(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
                'to': max(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
            } if self.transactions else {}
        }
    
    def to_database_records(self) -> List[Dict]:
        """Convert transactions to database-ready format"""
        records = []
        
        for tx in self.transactions:
            # Extract ticker from product name (simplified)
            ticker = self._extract_ticker(tx.get('product_name', ''))
            
            records.append({
                'timestamp': tx.get('timestamp') or datetime.now(),
                'ticker_symbol': ticker,
                'isin': tx.get('isin'),
                'platform': 'BG_SAXO',
                'operation_type': tx.get('operation_type'),
                'quantity': tx.get('quantity'),
                'price_unit': tx.get('price_unit'),
                'fiat_amount': tx.get('fiat_amount'),
                'currency_original': 'EUR',
                'status': 'VERIFIED',
                'notes': f"Imported from PDF: {self.file_path.name}",
            })
        
        return records
    
    def _extract_ticker(self, product_name: str) -> str:
        """Extract ticker symbol from product name (best effort)"""
        if not product_name:
            return 'UNKNOWN'
        
        # Common patterns for ADRs and known stocks
        ticker_hints = {
            'Alphabet': 'GOOGL',
            'ServiceNow': 'NOW',
            'CRISPR': 'CRSP',
            'Meta': 'META',
            'Apple': 'AAPL',
            'Tesla': 'TSLA',
            'Microsoft': 'MSFT',
            'NVIDIA': 'NVDA',
            'Amazon': 'AMZN',
            'Intel': 'INTC',
            'Palantir': 'PLTR',
            'QuantumScape': 'QS',
            'Nokia': 'NOKIA',
            'PayPal': 'PYPL',
            'Oracle': 'ORCL',
            'Ferrari': 'RACE',
        }
        
        for hint, ticker in ticker_hints.items():
            if hint.lower() in product_name.lower():
                return ticker
        
        # Return first word as fallback
        return product_name.split()[0][:10] if product_name else 'UNKNOWN'


def parse_bgsaxo_transactions_pdf(file_path: str) -> List[Dict]:
    """Convenience function to parse BG Saxo transactions PDF"""
    parser = BGSaxoTransactionsPDFParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/BGSAXO/Transactions_19807401_2024-11-26_2025-12-19.pdf"
    
    parser = BGSaxoTransactionsPDFParser(file_path)
    transactions = parser.parse()
    
    print("\n📊 Parsed Transactions (first 10):")
    for i, tx in enumerate(transactions[:10]):
        print(f"  {i+1}. {tx['timestamp'].strftime('%Y-%m-%d') if tx['timestamp'] else 'N/A'} | "
              f"{tx['operation_type']:8} | {tx['product_name'][:30]:30} | "
              f"Qty: {tx['quantity']} @ {tx['price_unit']}")
    
    print(f"\n📈 Summary:")
    summary = parser.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
