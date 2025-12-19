"""
WAR ROOM - Binance CSV Parser
Parses transaction history exports from Binance
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict
from pathlib import Path
from loguru import logger


class BinanceCSVParser:
    """
    Parser for Binance transaction history CSV exports.
    
    CSV format:
    id, datetime_tz_CET, type, label, market_model_type, order_type,
    sent_amount, sent_currency, sent_value_EUR, sent_address,
    received_amount, received_currency, received_value_EUR, received_address,
    fee_amount, fee_currency, fee_value_EUR
    
    Supports:
    - Receive/Reward (staking rewards)
    - Deposit (fiat deposits)
    - Buy/Sell/Trade (spot trades)
    - Send (withdrawals)
    - Receive (crypto deposits)
    """
    
    # Transaction type mapping
    TYPE_MAP = {
        'Receive': 'RECEIVE',
        'Send': 'SEND',
        'Deposit': 'DEPOSIT',
        'Buy': 'BUY',
        'Sell': 'SELL',
        'Trade': 'TRADE',
    }
    
    # Label mapping for more specific types
    LABEL_MAP = {
        'Reward': 'STAKING_REWARD',
        'Airdrop': 'AIRDROP',
        'Payment': 'PAYMENT',
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.transactions = []
        
    def parse(self) -> List[Dict]:
        """Parse all transactions from the CSV"""
        logger.info(f"Parsing Binance transactions from: {self.file_path}")
        
        self.transactions = []
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                tx = self._parse_row(row)
                if tx:
                    self.transactions.append(tx)
        
        logger.info(f"Successfully parsed {len(self.transactions)} transactions")
        return self.transactions
    
    def _parse_row(self, row: Dict) -> Dict:
        """Parse a single transaction row"""
        # Parse datetime
        tx_date = None
        datetime_str = row.get('datetime_tz_CET', '')
        try:
            # Format: 2024-01-01-01:00:00
            tx_date = datetime.strptime(datetime_str, '%Y-%m-%d-%H:%M:%S')
        except:
            pass
        
        # Get transaction type
        tx_type = row.get('type', '')
        label = row.get('label', '')
        market_type = row.get('market_model_type', '')
        order_type = row.get('order_type', '')
        
        # Map to internal type
        final_type = self.TYPE_MAP.get(tx_type, 'OTHER')
        if label:
            final_type = self.LABEL_MAP.get(label, final_type)
        
        # Parse amounts
        sent_amount = self._parse_number(row.get('sent_amount'))
        sent_currency = row.get('sent_currency', '')
        sent_value_eur = self._parse_number(row.get('sent_value_EUR'))
        
        received_amount = self._parse_number(row.get('received_amount'))
        received_currency = row.get('received_currency', '')
        received_value_eur = self._parse_number(row.get('received_value_EUR'))
        
        fee_amount = self._parse_number(row.get('fee_amount'))
        fee_currency = row.get('fee_currency', '')
        fee_value_eur = self._parse_number(row.get('fee_value_EUR'))
        
        # Determine primary amount and currency
        if received_amount > 0:
            primary_amount = received_amount
            primary_currency = received_currency
            fiat_amount = received_value_eur
        else:
            primary_amount = sent_amount
            primary_currency = sent_currency
            fiat_amount = -sent_value_eur if sent_value_eur > 0 else Decimal('0')
        
        return {
            'id': row.get('id', ''),
            'timestamp': tx_date,
            'operation_type': final_type,
            'label': label,
            'market_type': market_type,
            'order_type': order_type,
            'amount': primary_amount,
            'currency': primary_currency,
            'fiat_amount': fiat_amount,
            'sent_amount': sent_amount,
            'sent_currency': sent_currency,
            'sent_value_eur': sent_value_eur,
            'received_amount': received_amount,
            'received_currency': received_currency,
            'received_value_eur': received_value_eur,
            'fee_amount': fee_amount,
            'fee_currency': fee_currency,
            'fee_value_eur': fee_value_eur,
            'platform': 'BINANCE',
            'status': 'VERIFIED',
        }
    
    def _parse_number(self, value) -> Decimal:
        """Parse number from string"""
        if not value or value == '':
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
        currencies = set()
        total_fees_eur = Decimal('0')
        
        for tx in self.transactions:
            op = tx.get('operation_type', 'UNKNOWN')
            by_type[op] = by_type.get(op, 0) + 1
            if tx.get('currency'):
                currencies.add(tx['currency'])
            total_fees_eur += tx.get('fee_value_eur', Decimal('0'))
        
        return {
            'total_transactions': len(self.transactions),
            'by_operation': by_type,
            'currencies': list(currencies),
            'total_fees_eur': float(total_fees_eur),
            'date_range': {
                'from': min(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
                'to': max(tx['timestamp'] for tx in self.transactions if tx.get('timestamp')),
            } if self.transactions else {}
        }
    
    def get_staking_rewards(self) -> List[Dict]:
        """Get only staking reward transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') == 'STAKING_REWARD']
    
    def get_trades(self) -> List[Dict]:
        """Get only trade transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') in ('BUY', 'SELL', 'TRADE')]
    
    def get_deposits(self) -> List[Dict]:
        """Get only deposit transactions"""
        return [tx for tx in self.transactions if tx.get('operation_type') == 'DEPOSIT']


def parse_binance_csv(file_path: str) -> List[Dict]:
    """Convenience function to parse Binance CSV"""
    parser = BinanceCSVParser(file_path)
    return parser.parse()


def parse_all_binance_csvs(directory: str) -> List[Dict]:
    """Parse all Binance CSV files in a directory"""
    all_transactions = []
    dir_path = Path(directory)
    
    for csv_file in dir_path.glob('*.csv'):
        logger.info(f"Processing: {csv_file.name}")
        parser = BinanceCSVParser(str(csv_file))
        transactions = parser.parse()
        all_transactions.extend(transactions)
    
    # Sort by timestamp
    all_transactions.sort(key=lambda x: x.get('timestamp') or datetime.min)
    
    logger.info(f"Total transactions from all files: {len(all_transactions)}")
    return all_transactions


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "D:/Download/Binance/2025_05_17_19_26_07.csv"
    
    parser = BinanceCSVParser(file_path)
    transactions = parser.parse()
    
    print(f"\n📊 Total Transactions: {len(transactions)}")
    
    if transactions:
        print("\n📋 Sample transactions (first 20):")
        for i, tx in enumerate(transactions[:20]):
            date_str = tx['timestamp'].strftime('%Y-%m-%d') if tx.get('timestamp') else 'N/A'
            curr = tx.get('currency') or '-'
            amount = tx.get('amount', 0)
            print(f"  {i+1}. {date_str} | {tx['operation_type']:15} | {amount:15.8f} {curr:6} | €{tx['fiat_amount']:.4f}")
        
        print("\n📈 Summary:")
        summary = parser.get_summary()
        for key, value in summary.items():
            if key != 'currencies':
                print(f"  {key}: {value}")
        
        print(f"\n💎 Currencies traded: {len(summary['currencies'])}")
        print(f"  {', '.join(sorted(summary['currencies']))}")
