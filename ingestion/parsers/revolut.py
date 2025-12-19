"""
WAR ROOM - Revolut PDF Statement Parser
Parses account statements from Revolut (EUR accounts)
"""
import fitz  # PyMuPDF
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict
from pathlib import Path
from loguru import logger


class RevolutPDFParser:
    """
    Parser for Revolut account statement PDFs.
    
    Revolut PDFs contain transactions with:
    - Date
    - Description (with details like card number, recipient)
    - Money out (Denaro in uscita)
    - Money in (Denaro in entrata)
    - Balance
    """
    
    # Italian month mapping
    MONTH_MAP = {
        'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8,
        'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
    }
    
    # Transaction type patterns
    TRANSACTION_PATTERNS = {
        r'Transfer to Revolut Digital Assets.*Purchase of (\w+)': 'CRYPTO_BUY',
        r'Transfer from Revolut Digital Assets.*Sale of (\w+)': 'CRYPTO_SELL',
        r'To investment account': 'INVESTMENT_BUY',
        r'From investment account': 'INVESTMENT_SELL',
        r'Pagamento da': 'DEPOSIT',
        r'Ricarica': 'DEPOSIT',
        r'Prelievo di contanti': 'WITHDRAW_CASH',
        r'Prelievo da Pocket': 'INTERNAL_TRANSFER',
        r'Accredita.*Risparmi': 'SAVINGS_TRANSFER',
        r'Dividend': 'DIVIDEND',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.doc = None
        self.transactions = []
        
    def parse(self) -> List[Dict]:
        """Parse all transactions from the PDF"""
        logger.info(f"Parsing Revolut statement from: {self.file_path}")
        
        self.doc = fitz.open(str(self.file_path))
        total_pages = len(self.doc)
        logger.info(f"PDF has {total_pages} pages")
        
        self.transactions = []
        
        # Parse all pages
        for page_num in range(total_pages):
            page = self.doc[page_num]
            text = page.get_text()
            page_transactions = self._parse_page(text)
            self.transactions.extend(page_transactions)
            
            if (page_num + 1) % 10 == 0:
                logger.info(f"Processed {page_num + 1}/{total_pages} pages, found {len(self.transactions)} transactions")
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_page(self, text: str) -> List[Dict]:
        """Parse transactions from a single page"""
        transactions = []
        lines = text.split('\n')
        
        i = 0
        current_year = datetime.now().year
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Match date pattern: "2 ott 2023" or "11 feb 2020"
            date_match = re.match(r'^(\d{1,2})\s+([a-z]{3})\s+(\d{4})$', line.lower())
            if date_match:
                day, month_str, year = date_match.groups()
                month = self.MONTH_MAP.get(month_str, 1)
                try:
                    tx_date = datetime(int(year), month, int(day))
                except:
                    i += 1
                    continue
                
                # Next line should be description
                if i + 1 < len(lines):
                    description = lines[i + 1].strip()
                    
                    # Look for amounts in following lines
                    amount_out = Decimal('0')
                    amount_in = Decimal('0')
                    balance = Decimal('0')
                    extra_info = []
                    
                    for j in range(i + 2, min(len(lines), i + 12)):
                        check_line = lines[j].strip()
                        
                        # Check for next date (end of this transaction)
                        if re.match(r'^\d{1,2}\s+[a-z]{3}\s+\d{4}$', check_line.lower()):
                            break
                        
                        # Amount patterns (€123.45 or €1,234.56)
                        amount_match = re.match(r'^€([\d,]+\.\d{2})$', check_line)
                        if amount_match:
                            amount = self._parse_number(amount_match.group(1))
                            if amount_out == 0 and 'uscita' not in check_line.lower():
                                amount_out = amount
                            elif amount_in == 0:
                                amount_in = amount
                            else:
                                balance = amount
                            continue
                        
                        # Collect extra info (card, reference, etc.)
                        if check_line.startswith('A:') or check_line.startswith('Da:') or \
                           check_line.startswith('Carta:') or check_line.startswith('Riferimento:') or \
                           check_line.startswith('Costo:') or check_line.startswith('Purchase of') or \
                           check_line.startswith('Sale of'):
                            extra_info.append(check_line)
                    
                    # Determine transaction type
                    tx_type = self._classify_transaction(description, extra_info)
                    
                    # Extract crypto symbol if applicable
                    crypto_symbol = None
                    for info in extra_info:
                        crypto_match = re.search(r'(Purchase|Sale) of (\w+)', info)
                        if crypto_match:
                            crypto_symbol = crypto_match.group(2)
                    
                    transactions.append({
                        'timestamp': tx_date,
                        'description': description,
                        'operation_type': tx_type,
                        'amount_out': amount_out,
                        'amount_in': amount_in,
                        'fiat_amount': amount_in if amount_in > 0 else -amount_out,
                        'balance': balance,
                        'crypto_symbol': crypto_symbol,
                        'extra_info': ' | '.join(extra_info),
                        'platform': 'REVOLUT',
                        'status': 'VERIFIED',
                    })
            
            i += 1
        
        return transactions
    
    def _classify_transaction(self, description: str, extra_info: List[str]) -> str:
        """Classify transaction based on description"""
        full_text = description + ' ' + ' '.join(extra_info)
        
        for pattern, tx_type in self.TRANSACTION_PATTERNS.items():
            if re.search(pattern, full_text, re.IGNORECASE):
                return tx_type
        
        # Default classification based on amount direction
        return 'PAYMENT'  # Most transactions are payments
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from EUR format"""
        if not value:
            return Decimal('0')
        
        value_str = str(value).strip()
        value_str = re.sub(r'[€\s]', '', value_str)
        value_str = value_str.replace(',', '')  # Remove thousands separator
        
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
        crypto_buys = []
        
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
            total_in += tx.get('amount_in', Decimal('0'))
            total_out += tx.get('amount_out', Decimal('0'))
            
            if op == 'CRYPTO_BUY' and tx.get('crypto_symbol'):
                crypto_buys.append(tx['crypto_symbol'])
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'total_money_in': float(total_in),
            'total_money_out': float(total_out),
            'crypto_purchases': list(set(crypto_buys)),
            'date_range': {
                'from': min(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
                'to': max(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
            } if self.transactions else {}
        }
    
    def get_crypto_transactions(self) -> List[Dict]:
        """Get only crypto-related transactions"""
        return [tx for tx in self.transactions 
                if tx.get('operation_type') in ('CRYPTO_BUY', 'CRYPTO_SELL')]
    
    def get_investment_transactions(self) -> List[Dict]:
        """Get only investment-related transactions"""
        return [tx for tx in self.transactions 
                if tx.get('operation_type') in ('INVESTMENT_BUY', 'INVESTMENT_SELL', 'DIVIDEND')]


def parse_revolut_pdf(file_path: str) -> List[Dict]:
    """Convenience function to parse Revolut PDF"""
    parser = RevolutPDFParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/Revolut/account-statement_2020-01-01_2025-12-19_it-it_a1ebdb.pdf"
    
    parser = RevolutPDFParser(file_path)
    transactions = parser.parse()
    
    print(f"\n📊 Total Transactions: {len(transactions)}")
    
    if transactions:
        print("\n📋 Sample transactions (first 15):")
        for i, tx in enumerate(transactions[:15]):
            date_str = tx['timestamp'].strftime('%Y-%m-%d') if tx.get('timestamp') else 'N/A'
            amount = tx.get('amount_out') or tx.get('amount_in') or 0
            print(f"  {i+1}. {date_str} | {tx['operation_type']:15} | {tx['description'][:35]:35} | €{amount}")
        
        print("\n📈 Summary:")
        summary = parser.get_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Crypto summary
        crypto_txs = parser.get_crypto_transactions()
        if crypto_txs:
            print(f"\n💰 Crypto Transactions: {len(crypto_txs)}")
            for tx in crypto_txs[:5]:
                print(f"  - {tx['timestamp'].strftime('%Y-%m-%d')} | {tx['crypto_symbol']} | €{tx['amount_out']}")
