"""
WAR ROOM - Interactive Brokers (IBKR) CSV Parser
Parses transaction history CSV exports from IBKR
"""
import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict
from pathlib import Path
from loguru import logger


class IBKRCSVParser:
    """
    Parser for IBKR transaction history CSV exports.
    
    CSV format:
    - Header rows with metadata
    - Transaction History section with:
      Date, Account, Description, Transaction Type, Symbol, Quantity, Price, Gross Amount, Commission, Net Amount
    
    Supports:
    - Buy/Sell trades
    - Deposits/Withdrawals
    - Dividends
    - Forex conversions
    - Adjustments
    """
    
    # Transaction type mapping
    TYPE_MAP = {
        'Buy': 'BUY',
        'Sell': 'SELL',
        'Deposit': 'DEPOSIT',
        'Withdrawal': 'WITHDRAW',
        'Dividend': 'DIVIDEND',
        'Withholding Tax': 'TAX',
        'Forex Trade Component': 'FOREX',
        'Adjustment': 'ADJUSTMENT',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.transactions = []
        self.metadata = {}
        
    def parse(self) -> List[Dict]:
        """Parse all transactions from the CSV"""
        logger.info(f"Parsing IBKR transactions from: {self.file_path}")
        
        self.transactions = []
        self.metadata = {}
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            in_transactions = False
            header = []
            
            for row in reader:
                if len(row) < 2:
                    continue
                
                section = row[0]
                row_type = row[1]
                
                # Parse metadata
                if section == 'Statement' and row_type == 'Data':
                    if len(row) >= 4:
                        self.metadata[row[2]] = row[3]
                
                # Parse summary
                if section == 'Summary' and row_type == 'Data':
                    if len(row) >= 4:
                        self.metadata[f"summary_{row[2]}"] = row[3]
                
                # Check for transaction header
                if section == 'Transaction History' and row_type == 'Header':
                    header = row[2:]  # Skip section and type columns
                    in_transactions = True
                    continue
                
                # Parse transaction data
                if section == 'Transaction History' and row_type == 'Data' and in_transactions:
                    data = row[2:]  # Skip section and type columns
                    
                    if len(data) >= 10:
                        tx = self._parse_transaction_row(header, data)
                        if tx:
                            self.transactions.append(tx)
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_transaction_row(self, header: List[str], data: List[str]) -> Dict:
        """Parse a single transaction row"""
        # Create dict from header and data
        row_dict = {}
        for i, col in enumerate(header):
            if i < len(data):
                row_dict[col] = data[i]
        
        # Parse date
        tx_date = None
        date_str = row_dict.get('Date', '')
        try:
            tx_date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            pass
        
        # Parse transaction type
        tx_type_raw = row_dict.get('Transaction Type', '')
        tx_type = self.TYPE_MAP.get(tx_type_raw, 'OTHER')
        
        # Parse amounts
        quantity = self._parse_number(row_dict.get('Quantity', ''))
        price = self._parse_number(row_dict.get('Price', ''))
        gross_amount = self._parse_number(row_dict.get('Gross Amount ', ''))  # Note trailing space
        commission = self._parse_number(row_dict.get('Commission', ''))
        net_amount = self._parse_number(row_dict.get('Net Amount', ''))
        
        # Get symbol and description
        symbol = row_dict.get('Symbol', '')
        description = row_dict.get('Description', '')
        
        # Skip forex micro-transactions (very small amounts)
        if tx_type == 'FOREX' and abs(net_amount) < Decimal('0.01'):
            return None
        
        return {
            'timestamp': tx_date,
            'symbol': symbol if symbol != '-' else None,
            'description': description,
            'operation_type': tx_type,
            'quantity': quantity if quantity else None,
            'price': price if price else None,
            'gross_amount': gross_amount,
            'commission': commission,
            'net_amount': net_amount,
            'fiat_amount': net_amount,
            'platform': 'IBKR',
            'status': 'VERIFIED',
        }
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from string"""
        if not value or value == '-':
            return Decimal('0')
        
        value_str = str(value).strip()
        
        try:
            return Decimal(value_str)
        except InvalidOperation:
            return Decimal('0')
    
    def get_summary(self) -> Dict:
        """Get summary of parsed transactions"""
        if not self.transactions:
            return {'total_transactions': 0}
        
        by_type = {}
        symbols = set()
        
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
            if tx.get('symbol'):
                symbols.add(tx['symbol'])
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'symbols_traded': list(symbols),
            'metadata': self.metadata,
            'date_range': {
                'from': min(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
                'to': max(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
            } if self.transactions else {}
        }
    
    def get_trades(self) -> List[Dict]:
        """Get only trade transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') in ('BUY', 'SELL')]


def parse_ibkr_csv(file_path: str) -> List[Dict]:
    """Convenience function to parse IBKR CSV"""
    parser = IBKRCSVParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/IBKR/U22156212.TRANSACTIONS.1Y.csv"
    
    parser = IBKRCSVParser(file_path)
    transactions = parser.parse()
    
    print(f"\n📊 Total Transactions: {len(transactions)}")
    
    if transactions:
        print("\n📋 All transactions:")
        for i, tx in enumerate(transactions):
            date_str = tx['timestamp'].strftime('%Y-%m-%d') if tx.get('timestamp') else 'N/A'
            symbol = tx.get('symbol') or '-'
            qty = f"x{tx['quantity']}" if tx.get('quantity') else ''
            print(f"  {i+1}. {date_str} | {tx['operation_type']:10} | {symbol:10} {qty:8} | €{tx['net_amount']:.2f}")
        
        print("\n📈 Summary:")
        summary = parser.get_summary()
        for key, value in summary.items():
            if key != 'metadata':
                print(f"  {key}: {value}")
