"""
WAR ROOM - Trade Republic PDF Statement Parser
Parses account statements (Estratto conto) from Trade Republic
"""
import fitz  # PyMuPDF
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict
from pathlib import Path
from loguru import logger


class TradeRepublicPDFParser:
    """
    Parser for Trade Republic PDF account statements (Estratto conto).
    
    Format:
    DATA | TIPO | DESCRIZIONE | IN ENTRATA | IN USCITA | SALDO
    
    Supports:
    - Bonifico (deposits/withdrawals)
    - Commercio (Buy/Sell trades with ISIN and quantity)
    - Rendimento (Dividends)
    - Interessi (Interest payments)
    - Imposte (Taxes)
    """
    
    # Italian month mapping
    MONTH_MAP = {
        'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8,
        'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
    }
    
    # Transaction type mapping
    TYPE_MAP = {
        'Bonifico': 'TRANSFER',
        'Commercio': 'TRADE',
        'Rendimento': 'DIVIDEND',
        'Interessi': 'INTEREST',
        'Imposte': 'TAX',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = None
        self.transactions = []
        
    def parse(self) -> List[Dict]:
        """Parse all transactions from the PDF"""
        logger.info(f"Parsing Trade Republic statement from: {self.file_path}")
        
        self.doc = fitz.open(str(self.file_path))
        total_pages = len(self.doc)
        logger.info(f"PDF has {total_pages} pages")
        
        self.transactions = []
        
        # Get full text from all pages
        full_text = ""
        for page_num in range(total_pages):
            page = self.doc[page_num]
            full_text += page.get_text() + "\n"
        
        # Parse transactions
        self.transactions = self._parse_transactions(full_text)
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_transactions(self, text: str) -> List[Dict]:
        """Parse transactions from full PDF text"""
        transactions = []
        lines = text.split('\n')
        
        i = 0
        current_year = datetime.now().year
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Match date pattern: "19 set" or "01 ott"
            date_match = re.match(r'^(\d{1,2})\s+([a-z]{3})$', line.lower())
            if date_match:
                day = int(date_match.group(1))
                month_str = date_match.group(2)
                month = self.MONTH_MAP.get(month_str, 1)
                
                # Look for year in next line
                year = current_year
                if i + 1 < len(lines):
                    year_match = re.match(r'^(\d{4})$', lines[i + 1].strip())
                    if year_match:
                        year = int(year_match.group(1))
                        i += 1
                
                try:
                    tx_date = datetime(year, month, day)
                except:
                    i += 1
                    continue
                
                # Next line should be transaction type
                if i + 1 < len(lines):
                    tx_type_line = lines[i + 1].strip()
                    tx_type = None
                    
                    for type_name, type_code in self.TYPE_MAP.items():
                        if tx_type_line.startswith(type_name):
                            tx_type = type_code
                            break
                    
                    if tx_type:
                        # Parse description and amounts
                        description = ""
                        amount_in = Decimal('0')
                        amount_out = Decimal('0')
                        balance = Decimal('0')
                        isin = None
                        quantity = None
                        operation = None  # BUY or SELL
                        
                        # Get description from the type line (after the type keyword)
                        if tx_type == 'TRADE':
                            # Format: "Commercio Buy trade ISIN NAME, quantity: N"
                            trade_match = re.search(r'(Buy|Sell)\s+trade\s+([A-Z0-9]{12})\s+(.+?),\s*quantity:\s*(\d+)', tx_type_line)
                            if trade_match:
                                operation = 'BUY' if trade_match.group(1) == 'Buy' else 'SELL'
                                isin = trade_match.group(2)
                                description = trade_match.group(3)
                                quantity = int(trade_match.group(4))
                        elif tx_type == 'DIVIDEND':
                            # Format: "Rendimento Cash Dividend for ISIN XXXX"
                            div_match = re.search(r'ISIN\s+([A-Z0-9]{12})', tx_type_line)
                            if div_match:
                                isin = div_match.group(1)
                            description = tx_type_line
                        else:
                            description = tx_type_line
                        
                        # Look for amounts in following lines
                        for j in range(i + 2, min(len(lines), i + 6)):
                            amount_line = lines[j].strip()
                            
                            # Check for next date (end of transaction)
                            if re.match(r'^\d{1,2}\s+[a-z]{3}$', amount_line.lower()):
                                break
                            
                            # Amount pattern: "742,50 €" or "1.000,00 €"
                            amount_match = re.match(r'^([\d.,]+)\s*€$', amount_line)
                            if amount_match:
                                amount = self._parse_number(amount_match.group(1))
                                if amount_in == 0:
                                    amount_in = amount
                                elif amount_out == 0:
                                    amount_out = amount
                                else:
                                    balance = amount
                        
                        # Determine final operation type
                        final_type = tx_type
                        if tx_type == 'TRADE':
                            final_type = operation or 'TRADE'
                        elif tx_type == 'TRANSFER':
                            if 'Deposito' in description or 'Top up' in description:
                                final_type = 'DEPOSIT'
                            elif 'Outgoing' in description:
                                final_type = 'WITHDRAW'
                        
                        transactions.append({
                            'timestamp': tx_date,
                            'description': description,
                            'operation_type': final_type,
                            'isin': isin,
                            'quantity': quantity,
                            'amount_in': amount_in,
                            'amount_out': amount_out,
                            'fiat_amount': amount_in if amount_in > 0 else -amount_out,
                            'balance': balance,
                            'platform': 'TRADE_REPUBLIC',
                            'status': 'VERIFIED',
                        })
            
            i += 1
        
        return transactions
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from European format"""
        if not value:
            return Decimal('0')
        
        value_str = str(value).strip()
        value_str = re.sub(r'[€\s]', '', value_str)
        
        # Handle European format: 1.234,56 -> 1234.56
        if ',' in value_str:
            value_str = value_str.replace('.', '').replace(',', '.')
        
        try:
            return Decimal(value_str)
        except InvalidOperation:
            return Decimal('0')
    
    def get_summary(self) -> Dict:
        """Get summary of parsed transactions"""
        if not self.transactions:
            return {'total_transactions': 0}
        
        by_type = {}
        total_in = Decimal('0')
        total_out = Decimal('0')
        
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
            total_in += tx.get('amount_in', Decimal('0'))
            total_out += tx.get('amount_out', Decimal('0'))
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'total_in': float(total_in),
            'total_out': float(total_out),
            'date_range': {
                'from': min(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
                'to': max(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
            } if self.transactions else {}
        }
    
    def get_trades(self) -> List[Dict]:
        """Get only trade transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') in ('BUY', 'SELL')]
    
    def get_dividends(self) -> List[Dict]:
        """Get only dividend transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') == 'DIVIDEND']


def parse_trade_republic_pdf(file_path: str) -> List[Dict]:
    """Convenience function to parse Trade Republic PDF"""
    parser = TradeRepublicPDFParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/Trade Repubblic/Estratto conto.pdf"
    
    parser = TradeRepublicPDFParser(file_path)
    transactions = parser.parse()
    
    print(f"\n📊 Total Transactions: {len(transactions)}")
    
    if transactions:
        print("\n📋 Sample transactions (first 15):")
        for i, tx in enumerate(transactions[:15]):
            date_str = tx['timestamp'].strftime('%Y-%m-%d') if tx.get('timestamp') else 'N/A'
            isin = tx.get('isin') or ''
            qty = f"x{tx['quantity']}" if tx.get('quantity') else ''
            print(f"  {i+1}. {date_str} | {tx['operation_type']:10} | {isin:12} {qty:5} | €{tx['fiat_amount']}")
        
        print("\n📈 Summary:")
        summary = parser.get_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
