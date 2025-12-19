"""
WAR ROOM - Scalable Capital / Baader Bank PDF Parser
Parses Monthly Account Statements from Scalable Capital (via Baader Bank)
"""
import fitz  # PyMuPDF
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict
from pathlib import Path
from loguru import logger


class ScalableCapitalPDFParser:
    """
    Parser for Scalable Capital / Baader Bank Monthly Account Statement PDFs.
    
    These PDFs contain:
    - Direct Debit (deposits)
    - Purchase/Sale transactions with ISIN, quantity, amount
    - Interest payments
    """
    
    # Operation type patterns
    OPERATION_MAP = {
        'Purchase': 'BUY',
        'Sale': 'SELL',
        'Direct Debit': 'DEPOSIT',
        'Withdrawal': 'WITHDRAW',
        'Dividend': 'DIVIDEND',
        'Interest': 'INTEREST',
        'Fee': 'FEE',
        'Transfer': 'TRANSFER',
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
        logger.info(f"Parsing Scalable Capital statement from: {self.file_path}")
        
        self.doc = fitz.open(str(self.file_path))
        total_pages = len(self.doc)
        logger.info(f"PDF has {total_pages} pages")
        
        self.transactions = []
        
        # Parse all pages
        full_text = ""
        for page_num in range(total_pages):
            page = self.doc[page_num]
            full_text += page.get_text() + "\n"
        
        # Parse transactions from text
        self.transactions = self._parse_transactions(full_text)
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_transactions(self, text: str) -> List[Dict]:
        """Parse transactions from full PDF text"""
        transactions = []
        lines = text.split('\n')
        
        i = 0
        current_date = None
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for date pattern (YYYY-MM-DD)
            date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', line)
            if date_match:
                try:
                    current_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                except:
                    pass
                i += 1
                continue
            
            # Look for Direct Debit (Deposit)
            if 'Direct Debit' in line:
                # Look for amount in surrounding lines
                for j in range(max(0, i-3), min(len(lines), i+5)):
                    amount_match = re.search(r'(\d+[.,]\d{2})\s*$', lines[j])
                    if amount_match:
                        amount = self._parse_number(amount_match.group(1))
                        if amount > 0:
                            transactions.append({
                                'timestamp': current_date,
                                'product_name': 'Cash Deposit',
                                'operation_type': 'DEPOSIT',
                                'quantity': Decimal('1'),
                                'price_unit': amount,
                                'fiat_amount': amount,
                                'isin': None,
                                'platform': 'SCALABLE_CAPITAL',
                                'status': 'VERIFIED',
                            })
                            break
                i += 1
                continue
            
            # Look for Purchase/Sale
            if line.startswith('Purchase') or line.startswith('Sale'):
                operation = 'BUY' if 'Purchase' in line else 'SELL'
                
                # Format is:
                # Purchase (or Sale)
                # 62.27 -       <- amount
                # IS MSCI BRAZ.U.ETF USD D   <- product name
                # ISIN IE00B0M63516
                # STK               3
                
                amount = None
                product_name = None
                isin = None
                quantity = None
                
                for j in range(i + 1, min(len(lines), i + 10)):
                    check_line = lines[j].strip()
                    
                    # Amount pattern (number followed by - for debit)
                    if not amount:
                        amount_match = re.match(r'^(\d+[.,]\d{2})\s*-?$', check_line)
                        if amount_match:
                            amount = self._parse_number(amount_match.group(1))
                            continue
                    
                    # Product name (after amount, before ISIN)
                    if amount and not product_name and not check_line.startswith('ISIN') and not check_line.startswith('STK'):
                        if check_line and not re.match(r'^[\d.,\s-]+$', check_line) and 'Case No' not in check_line:
                            product_name = check_line
                            continue
                    
                    # ISIN pattern
                    isin_match = re.search(r'ISIN\s+([A-Z]{2}[A-Z0-9]{10})', check_line)
                    if isin_match:
                        isin = isin_match.group(1)
                        continue
                    
                    # Quantity pattern (STK = Stück = pieces)
                    qty_match = re.search(r'STK\s+(\d+)', check_line)
                    if qty_match:
                        quantity = Decimal(qty_match.group(1))
                        break  # We have all we need
                
                if product_name or isin:
                    transactions.append({
                        'timestamp': current_date,
                        'product_name': product_name or isin or 'Unknown',
                        'operation_type': operation,
                        'quantity': quantity or Decimal('1'),
                        'price_unit': (amount / quantity) if amount and quantity else Decimal('0'),
                        'fiat_amount': amount or Decimal('0'),
                        'isin': isin,
                        'platform': 'SCALABLE_CAPITAL',
                        'status': 'VERIFIED',
                    })
                
                i += 8  # Skip parsed lines
                continue
            
            # Look for Dividend
            if 'Dividend' in line:
                # Look for amount
                for j in range(i, min(len(lines), i + 5)):
                    amount_match = re.search(r'(\d+[.,]\d{2})', lines[j])
                    if amount_match:
                        amount = self._parse_number(amount_match.group(1))
                        transactions.append({
                            'timestamp': current_date,
                            'product_name': 'Dividend Payment',
                            'operation_type': 'DIVIDEND',
                            'quantity': Decimal('1'),
                            'price_unit': amount,
                            'fiat_amount': amount,
                            'isin': None,
                            'platform': 'SCALABLE_CAPITAL',
                            'status': 'VERIFIED',
                        })
                        break
            
            i += 1
        
        return transactions
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from European or US format"""
        if not value:
            return Decimal('0')
        
        value_str = str(value).strip()
        value_str = re.sub(r'[€$£\s]', '', value_str)
        
        # Handle European format: 1.234,56 -> 1234.56
        if ',' in value_str and '.' in value_str:
            value_str = value_str.replace('.', '').replace(',', '.')
        elif ',' in value_str:
            value_str = value_str.replace(',', '.')
        
        try:
            return Decimal(value_str)
        except InvalidOperation:
            return Decimal('0')
    
    def get_summary(self) -> Dict:
        """Get summary of parsed transactions"""
        if not self.transactions:
            return {'total_transactions': 0}
        
        by_type = {}
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'file': self.file_path.name,
        }


def parse_scalable_pdf(file_path: str) -> List[Dict]:
    """Convenience function to parse Scalable Capital PDF"""
    parser = ScalableCapitalPDFParser(file_path)
    return parser.parse()


def parse_all_scalable_pdfs(directory: str) -> List[Dict]:
    """Parse all Scalable Capital PDFs in a directory"""
    all_transactions = []
    folder = Path(directory)
    
    for pdf_file in folder.glob('*.pdf'):
        if 'Monthly account statement' in pdf_file.name or 'Statement' in pdf_file.name:
            try:
                parser = ScalableCapitalPDFParser(str(pdf_file))
                transactions = parser.parse()
                all_transactions.extend(transactions)
                logger.info(f"  {pdf_file.name}: {len(transactions)} transactions")
            except Exception as e:
                logger.warning(f"  {pdf_file.name}: Error - {e}")
    
    return all_transactions


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "D:/Download/SCALABLE CAPITAL"
    
    if Path(path).is_dir():
        # Parse all PDFs in directory
        print(f"\n📂 Parsing all PDFs in: {path}")
        transactions = parse_all_scalable_pdfs(path)
    else:
        # Parse single file
        parser = ScalableCapitalPDFParser(path)
        transactions = parser.parse()
    
    print(f"\n📊 Total Transactions: {len(transactions)}")
    
    if transactions:
        print("\n📋 Sample transactions:")
        for i, tx in enumerate(transactions[:10]):
            date_str = tx['timestamp'].strftime('%Y-%m-%d') if tx.get('timestamp') else 'N/A'
            print(f"  {i+1}. {date_str} | {tx['operation_type']:8} | {tx['product_name'][:30]:30} | €{tx['fiat_amount']}")
        
        # Summary by type
        summary = {}
        for tx in transactions:
            op = tx['operation_type']
            summary[op] = summary.get(op, 0) + 1
        print(f"\n📈 By operation: {summary}")
