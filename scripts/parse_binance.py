"""
Parse Binance Transaction History CSV.
Extracts: holdings, transactions, cash (EUR/USDT/USDC).
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction


# Currencies to treat as CASH
CASH_CURRENCIES = ['EUR', 'USD', 'USDT', 'USDC']


def parse_amount(value: str) -> Decimal:
    """Parse amount to Decimal."""
    if not value or value == '-' or value == '':
        return Decimal('0')
    try:
        return Decimal(str(float(value)))
    except (ValueError, InvalidOperation):
        return Decimal('0')


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime like '2024-01-01-01:00:00' to datetime."""
    try:
        # Format: 2024-01-01-01:00:00
        return datetime.strptime(dt_str, '%Y-%m-%d-%H:%M:%S')
    except:
        return None


def parse_binance_csv(csv_path: str):
    """Parse Binance CSV for complete data."""
    print("=" * 70)
    print("📊 PARSING BINANCE")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Binance data
    deleted_h = session.query(Holding).filter(Holding.broker == 'BINANCE').delete()
    deleted_t = session.query(Transaction).filter(Transaction.broker == 'BINANCE').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted_h} holdings, {deleted_t} transactions")
    
    # Track net positions
    positions = defaultdict(lambda: {'qty': Decimal('0'), 'value_eur': Decimal('0')})
    
    transactions = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            tx_type = row.get('type', '')
            label = row.get('label', '')
            tx_datetime = parse_datetime(row.get('datetime_tz_CET', ''))
            
            if not tx_datetime:
                continue
            
            # Parse amounts
            sent_amount = parse_amount(row.get('sent_amount', ''))
            sent_currency = row.get('sent_currency', '')
            sent_value_eur = parse_amount(row.get('sent_value_EUR', ''))
            
            received_amount = parse_amount(row.get('received_amount', ''))
            received_currency = row.get('received_currency', '')
            received_value_eur = parse_amount(row.get('received_value_EUR', ''))
            
            fee_amount = parse_amount(row.get('fee_amount', ''))
            fee_currency = row.get('fee_currency', '')
            fee_value_eur = parse_amount(row.get('fee_value_EUR', ''))
            
            # Update positions based on transaction type
            if tx_type == 'Trade' or tx_type == 'Buy' or tx_type == 'Sell':
                # Sent (outflow)
                if sent_currency and sent_amount > 0:
                    positions[sent_currency]['qty'] -= sent_amount
                    positions[sent_currency]['value_eur'] -= sent_value_eur
                
                # Received (inflow)
                if received_currency and received_amount > 0:
                    positions[received_currency]['qty'] += received_amount
                    positions[received_currency]['value_eur'] += received_value_eur
                
                # Fees
                if fee_currency and fee_amount > 0:
                    positions[fee_currency]['qty'] -= fee_amount
                
                # Record transaction
                if tx_type == 'Buy':
                    transactions.append({
                        'date': tx_datetime,
                        'type': 'BUY',
                        'symbol': received_currency,
                        'qty': received_amount,
                        'price': sent_value_eur / received_amount if received_amount > 0 else Decimal('0'),
                        'amount': sent_value_eur,
                        'fees': fee_value_eur
                    })
                elif tx_type == 'Sell':
                    transactions.append({
                        'date': tx_datetime,
                        'type': 'SELL',
                        'symbol': sent_currency,
                        'qty': sent_amount,
                        'price': received_value_eur / sent_amount if sent_amount > 0 else Decimal('0'),
                        'amount': received_value_eur,
                        'fees': fee_value_eur
                    })
                elif tx_type == 'Trade':
                    # Trade is a swap between currencies
                    transactions.append({
                        'date': tx_datetime,
                        'type': 'TRADE',
                        'symbol': f"{sent_currency}->{received_currency}",
                        'qty': received_amount,
                        'price': sent_value_eur / received_amount if received_amount > 0 else Decimal('0'),
                        'amount': sent_value_eur,
                        'fees': fee_value_eur
                    })
            
            elif tx_type == 'Receive':
                # Deposits, rewards, payments
                if received_currency and received_amount > 0:
                    positions[received_currency]['qty'] += received_amount
                    positions[received_currency]['value_eur'] += received_value_eur
                
                if label == 'Reward':
                    transactions.append({
                        'date': tx_datetime,
                        'type': 'REWARD',
                        'symbol': received_currency,
                        'qty': received_amount,
                        'price': received_value_eur / received_amount if received_amount > 0 else Decimal('0'),
                        'amount': received_value_eur,
                        'fees': Decimal('0')
                    })
                else:
                    transactions.append({
                        'date': tx_datetime,
                        'type': 'DEPOSIT',
                        'symbol': received_currency,
                        'qty': received_amount,
                        'price': Decimal('1') if received_currency in CASH_CURRENCIES else (
                            received_value_eur / received_amount if received_amount > 0 else Decimal('0')
                        ),
                        'amount': received_value_eur,
                        'fees': Decimal('0')
                    })
            
            elif tx_type == 'Send':
                # Withdrawals
                if sent_currency and sent_amount > 0:
                    positions[sent_currency]['qty'] -= sent_amount
                    positions[sent_currency]['value_eur'] -= sent_value_eur
                
                transactions.append({
                    'date': tx_datetime,
                    'type': 'WITHDRAWAL',
                    'symbol': sent_currency,
                    'qty': sent_amount,
                    'price': sent_value_eur / sent_amount if sent_amount > 0 else Decimal('0'),
                    'amount': sent_value_eur,
                    'fees': fee_value_eur
                })
            
            elif tx_type == 'Deposit':
                # FIAT deposits
                if received_currency and received_amount > 0:
                    positions[received_currency]['qty'] += received_amount
                    positions[received_currency]['value_eur'] += received_value_eur
                
                transactions.append({
                    'date': tx_datetime,
                    'type': 'DEPOSIT',
                    'symbol': received_currency,
                    'qty': received_amount,
                    'price': Decimal('1'),
                    'amount': received_value_eur,
                    'fees': fee_value_eur
                })
    
    # Filter out zero/negative positions and separate cash from crypto
    cash_holdings = {}
    crypto_holdings = {}
    
    for currency, data in positions.items():
        if data['qty'] > Decimal('0.00001'):  # Small threshold to filter dust
            if currency in CASH_CURRENCIES:
                cash_holdings[currency] = data
            else:
                crypto_holdings[currency] = data
    
    # Print summary
    print(f"\n📋 POSITIONS FOUND")
    print("-" * 50)
    
    total_cash = Decimal('0')
    for currency, data in sorted(cash_holdings.items()):
        print(f"  💵 {currency:<6} | {data['qty']:>15.4f} | €{data['value_eur']:>10.2f}")
        total_cash += data['qty'] if currency == 'EUR' else data['value_eur']
    
    for currency, data in sorted(crypto_holdings.items()):
        print(f"  🪙 {currency:<6} | {data['qty']:>15.8f} | €{data['value_eur']:>10.2f}")
    
    # Insert holdings
    print(f"\n📥 Inserting holdings...")
    
    # Cash holdings
    for currency, data in cash_holdings.items():
        try:
            holding = Holding(
                id=uuid.uuid4(),
                broker='BINANCE',
                ticker=currency,
                name=f'Cash ({currency})',
                asset_type='CASH',
                quantity=data['qty'],
                current_value=data['qty'] if currency == 'EUR' else data['value_eur'],
                current_price=Decimal('1'),
                purchase_price=Decimal('1'),
                currency=currency,
                source_document=Path(csv_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
            print(f"  💵 {currency}: {data['qty']:.4f}")
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error {currency}: {e}")
    
    # Crypto holdings
    for currency, data in crypto_holdings.items():
        try:
            avg_price = abs(data['value_eur'] / data['qty']) if data['qty'] > 0 else Decimal('0')
            holding = Holding(
                id=uuid.uuid4(),
                broker='BINANCE',
                ticker=currency,
                name=currency,
                asset_type='CRYPTO',
                quantity=data['qty'],
                current_value=abs(data['value_eur']),
                current_price=avg_price,
                currency='EUR',
                source_document=Path(csv_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
            print(f"  🪙 {currency}: {data['qty']:.8f}")
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error {currency}: {e}")
    
    # Insert transactions (sample - not all 1300+)
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    
    tx_counts = defaultdict(int)
    for tx in transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='BINANCE',
                ticker=tx['symbol'],
                operation=tx['type'],
                quantity=tx['qty'],
                price=tx['price'],
                total_amount=tx['amount'],
                currency='EUR',
                fees=tx['fees'],
                timestamp=tx['date'],
                source_document=Path(csv_path).name
            )
            session.add(transaction)
            session.commit()
            tx_counts[tx['type']] += 1
        except Exception as e:
            session.rollback()
    
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Cash Holdings:   {len(cash_holdings)}")
    print(f"  Crypto Holdings: {len(crypto_holdings)}")
    print(f"  Transactions:")
    for tx_type, count in sorted(tx_counts.items()):
        print(f"    {tx_type:<12}: {count}")
    print(f"    TOTAL       : {sum(tx_counts.values())}")
    print(f"=" * 70)
    
    return len(cash_holdings) + len(crypto_holdings) + len(transactions)


if __name__ == "__main__":
    csv_path = r'D:\Download\Binance\2025_05_17_19_26_07.csv'
    parse_binance_csv(csv_path)
