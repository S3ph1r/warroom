"""
Parse IBKR Transaction History CSV.
Extracts: cash balance, holdings, and all transactions.
"""
import sys
import csv
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction


def parse_amount(value: str) -> Decimal:
    """Parse amount to Decimal, handling scientific notation."""
    if not value or value == '-':
        return Decimal('0')
    try:
        return Decimal(str(float(value)))
    except:
        return Decimal('0')


def parse_date(date_str: str) -> datetime:
    """Parse date like '2025-12-18' to datetime."""
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d')
    except:
        return None


def parse_ibkr_complete(csv_path: str):
    """Parse IBKR Transaction History CSV for complete data."""
    print("=" * 70)
    print("📊 PARSING IBKR COMPLETE")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing IBKR data
    deleted_h = session.query(Holding).filter(Holding.broker == 'IBKR').delete()
    deleted_t = session.query(Transaction).filter(Transaction.broker == 'IBKR').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted_h} holdings, {deleted_t} transactions")
    
    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    
    cash_balance = Decimal('0')
    all_trades = []  # Collect all trades first
    
    for line in lines:
        parts = line.split(',')
        
        # Extract cash balance from Summary section
        if len(parts) >= 4 and parts[0] == 'Summary' and parts[1] == 'Data':
            if 'Liquidità finale' in parts[2]:
                cash_balance = parse_amount(parts[3])
                print(f"  💶 Cash Balance: €{cash_balance:.2f}")
        
        # Extract transactions
        if len(parts) >= 11 and parts[0] == 'Transaction History' and parts[1] == 'Data':
            tx_date = parse_date(parts[2])
            description = parts[4]
            tx_type = parts[5]  # Buy, Sell, Deposit, Adjustment, Forex Trade Component
            symbol = parts[6]
            qty = parse_amount(parts[7])
            price = parse_amount(parts[8])
            gross = parse_amount(parts[9])
            commission = parse_amount(parts[10])
            net = parse_amount(parts[11]) if len(parts) > 11 else gross + commission
            
            # Skip forex translations and adjustments
            if tx_type in ['Forex Trade Component', 'Adjustment']:
                continue
            
            # Collect all trades for later processing
            if tx_type in ['Buy', 'Sell', 'Deposit']:
                all_trades.append({
                    'date': tx_date,
                    'type': tx_type.upper(),
                    'symbol': symbol if tx_type != 'Deposit' else 'EUR_CASH',
                    'name': description,
                    'qty': abs(qty) if tx_type != 'Deposit' else net,
                    'price': abs(price) if tx_type != 'Deposit' else Decimal('1'),
                    'gross': abs(gross) if tx_type != 'Deposit' else net,
                    'commission': abs(commission) if tx_type != 'Deposit' else Decimal('0'),
                    'net': abs(net) if tx_type == 'Buy' else net
                })
    
    # Sort trades by date (oldest first) to calculate positions correctly
    all_trades.sort(key=lambda x: x['date'])
    
    # Now process trades in chronological order
    transactions = []
    holdings = {}  # symbol -> {qty, total_cost}
    
    for trade in all_trades:
        tx_type = trade['type']
        symbol = trade['symbol']
        
        if tx_type == 'DEPOSIT':
            transactions.append(trade)
            print(f"  📥 {trade['date'].strftime('%Y-%m-%d')} | DEPOSIT | €{trade['qty']:.2f}")
            
        elif tx_type == 'BUY':
            transactions.append(trade)
            print(f"  📈 {trade['date'].strftime('%Y-%m-%d')} | BUY  | {symbol:<6} | Qty: {trade['qty']:>4} | €{trade['gross']:>10.2f}")
            
            # Track holdings
            if symbol not in holdings:
                holdings[symbol] = {'qty': Decimal('0'), 'total_cost': Decimal('0'), 'name': trade['name']}
            holdings[symbol]['qty'] += trade['qty']
            holdings[symbol]['total_cost'] += trade['net']
            
        elif tx_type == 'SELL':
            transactions.append(trade)
            print(f"  📉 {trade['date'].strftime('%Y-%m-%d')} | SELL | {symbol:<6} | Qty: {trade['qty']:>4} | €{trade['gross']:>10.2f}")
            
            # Update holdings - subtract from position
            if symbol in holdings:
                holdings[symbol]['qty'] -= trade['qty']
    
    # Filter holdings (keep only non-zero positions)
    active_holdings = {k: v for k, v in holdings.items() if v['qty'] > 0}
    
    # Insert holdings
    print(f"\n📥 Inserting {len(active_holdings)} holdings...")
    for symbol, data in active_holdings.items():
        try:
            avg_price = data['total_cost'] / data['qty'] if data['qty'] > 0 else Decimal('0')
            holding = Holding(
                id=uuid.uuid4(),
                broker='IBKR',
                ticker=symbol,
                name=data['name'][:50],
                asset_type='STOCK',
                quantity=data['qty'],
                current_value=data['total_cost'],  # Use cost as current value for now
                current_price=avg_price,
                purchase_price=avg_price,
                currency='EUR',
                source_document=Path(csv_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
            print(f"  📊 {symbol:<6} | Qty: {data['qty']:>4} | Cost: €{data['total_cost']:.2f}")
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {e}")
    
    # Add cash holding
    if cash_balance > 0:
        cash_holding = Holding(
            id=uuid.uuid4(),
            broker='IBKR',
            ticker='CASH',
            name='Cash (EUR)',
            asset_type='CASH',
            quantity=cash_balance,
            current_value=cash_balance,
            current_price=Decimal('1'),
            purchase_price=Decimal('1'),
            currency='EUR',
            source_document=Path(csv_path).name,
            last_updated=datetime.now()
        )
        session.add(cash_holding)
        session.commit()
        print(f"  💶 CASH | €{cash_balance:.2f}")
    
    # Insert transactions
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    for tx in transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='IBKR',
                ticker=tx['symbol'],
                operation=tx['type'],
                quantity=tx['qty'],
                price=tx['price'],
                total_amount=tx['gross'],  # Changed from 'amount' to 'gross'
                currency='EUR',
                fees=tx['commission'],  # Changed from 'fees' to 'commission'
                timestamp=tx['date'],
                source_document=Path(csv_path).name,
                notes=tx['name'][:100]
            )
            session.add(transaction)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {str(e)[:50]}")
    
    session.close()
    
    buys = len([t for t in transactions if t['type'] == 'BUY'])
    sells = len([t for t in transactions if t['type'] == 'SELL'])
    deposits = len([t for t in transactions if t['type'] == 'DEPOSIT'])
    
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Holdings: {len(active_holdings)}")
    print(f"  Cash:     €{cash_balance:.2f}")
    print(f"  Buys:     {buys}")
    print(f"  Sells:    {sells}")
    print(f"  Deposits: {deposits}")
    print(f"  TOTAL TX: {len(transactions)}")
    print(f"=" * 70)
    
    return len(active_holdings) + len(transactions)


if __name__ == "__main__":
    csv_path = r'D:\Download\IBKR\U22156212.TRANSACTIONS.1Y.csv'
    parse_ibkr_complete(csv_path)
