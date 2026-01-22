"""
Parse Revolut Trading Account Statement PDF.
Extracts: stock holdings, cash balance, and all transactions.
Uses PyMuPDF (fitz) for text extraction.
"""
import sys
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

import fitz

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction


def parse_usd_amount(value: str) -> Decimal:
    """Parse USD amount like 'US$1,127.26' to Decimal."""
    if not value:
        return Decimal('0')
    clean = value.replace('US$', '').replace('$', '').replace(',', '').replace('-', '').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_date(date_str: str) -> datetime:
    """Parse date like '28 Dec 2019 00:49:41 GMT' to datetime."""
    try:
        # Try full format
        return datetime.strptime(date_str.split(' GMT')[0], '%d %b %Y %H:%M:%S')
    except:
        try:
            # Try simplified format
            return datetime.strptime(date_str[:11], '%d %b %Y')
        except:
            return None


def parse_revolut_stocks(pdf_path: str):
    """Parse Revolut Trading Account Statement PDF."""
    print("=" * 70)
    print("📊 PARSING REVOLUT STOCKS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Revolut Stock holdings and transactions
    deleted_h = session.query(Holding).filter(
        Holding.broker == 'REVOLUT',
        Holding.asset_type.in_(['STOCK', 'CASH'])
    ).delete(synchronize_session=False)
    deleted_t = session.query(Transaction).filter(
        Transaction.broker == 'REVOLUT',
        Transaction.operation.in_(['BUY', 'SELL', 'DIVIDEND', 'DEPOSIT', 'WITHDRAWAL'])
    ).delete(synchronize_session=False)
    session.commit()
    print(f"🗑️  Cleared {deleted_h} REVOLUT holdings, {deleted_t} transactions")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()
    
    lines = [l.strip() for l in all_text.split('\n') if l.strip()]
    
    holdings = []
    transactions = []
    cash_balance = Decimal('0')
    
    # Parse USD Portfolio breakdown section
    i = 0
    in_portfolio = False
    in_transactions = False
    
    while i < len(lines):
        line = lines[i]
        
        # Detect USD Portfolio section
        if 'USD Portfolio breakdown' in line:
            in_portfolio = True
            i += 1
            continue
        
        # Detect end of portfolio (stock totals)
        if in_portfolio and line == 'Stocks value':
            in_portfolio = False
            i += 1
            continue
        
        # Parse Cash value
        if line == 'Cash value' and i + 1 < len(lines):
            cash_val = lines[i + 1]
            if 'US$' in cash_val:
                cash_balance = parse_usd_amount(cash_val)
                print(f"  💵 Cash Balance: ${cash_balance:.2f}")
            i += 2
            continue
        
        # Parse holdings in USD Portfolio (Symbol, Company, ISIN, Qty, Price, Value, %)
        if in_portfolio:
            # Check if this looks like a symbol (uppercase letters only)
            if re.match(r'^[A-Z]{1,5}$', line):
                symbol = line
                if i + 5 < len(lines):
                    company = lines[i + 1]
                    isin = lines[i + 2]
                    qty = lines[i + 3]
                    price = lines[i + 4]
                    value = lines[i + 5]
                    
                    # Validate ISIN format
                    if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', isin):
                        holding = {
                            'symbol': symbol,
                            'name': company[:50],
                            'isin': isin,
                            'quantity': Decimal(qty),
                            'price': parse_usd_amount(price),
                            'value': parse_usd_amount(value)
                        }
                        holdings.append(holding)
                        print(f"  📊 {symbol:<6} | {company[:25]:<25} | {isin} | Qty: {qty} | ${parse_usd_amount(value):.2f}")
                        i += 6
                        continue
        
        # Detect USD Transactions section
        if 'USD Transactions' in line:
            in_transactions = True
            i += 1
            continue
        
        # Parse transactions
        if in_transactions:
            # Look for date pattern: "28 Dec 2019 00:49:41 GMT"
            date_match = re.match(r'^(\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2} GMT)$', line)
            if date_match:
                tx_date = parse_date(date_match.group(1))
                
                if tx_date and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    
                    # Cash top-up or withdrawal
                    if 'Cash top-up' in next_line:
                        if i + 2 < len(lines):
                            amount = parse_usd_amount(lines[i + 2])
                            transactions.append({
                                'date': tx_date,
                                'type': 'DEPOSIT',
                                'symbol': 'USD_CASH',
                                'qty': amount,
                                'price': Decimal('1'),
                                'amount': amount
                            })
                        i += 4
                        continue
                    
                    if 'Cash withdrawal' in next_line:
                        if i + 2 < len(lines):
                            amount = parse_usd_amount(lines[i + 2])
                            transactions.append({
                                'date': tx_date,
                                'type': 'WITHDRAWAL',
                                'symbol': 'USD_CASH',
                                'qty': amount,
                                'price': Decimal('1'),
                                'amount': amount
                            })
                        i += 4
                        continue
                    
                    # Trade (symbol on same or next line)
                    # Pattern: "SYMBOL Trade - Market/Limit" or just "SYMBOL" followed by "Trade -"
                    symbol_match = re.match(r'^([A-Z]{1,5})\s*(Trade|Dividend)', next_line)
                    if symbol_match:
                        symbol = symbol_match.group(1)
                        tx_type = 'DIVIDEND' if 'Dividend' in next_line else 'TRADE'
                        
                        # Look for quantity, price, side (Buy/Sell), value
                        j = i + 2
                        qty = Decimal('0')
                        price = Decimal('0')
                        operation = 'BUY'
                        amount = Decimal('0')
                        
                        while j < len(lines) and j < i + 8:
                            check = lines[j]
                            
                            # Quantity (number, possibly with decimals)
                            qty_match = re.match(r'^([\d.]+)$', check)
                            if qty_match and qty == 0:
                                qty = Decimal(qty_match.group(1))
                                j += 1
                                continue
                            
                            # Price and side (e.g., "US$9.97" or "Buy US$30")
                            if 'Buy' in check or 'Sell' in check:
                                operation = 'BUY' if 'Buy' in check else 'SELL'
                                amount = parse_usd_amount(check)
                                break
                            
                            # Price only
                            if 'US$' in check and price == 0:
                                price = parse_usd_amount(check)
                            
                            j += 1
                        
                        if tx_type == 'DIVIDEND':
                            # Dividend amount is in next line
                            amount = parse_usd_amount(lines[i + 2]) if i + 2 < len(lines) else Decimal('0')
                            transactions.append({
                                'date': tx_date,
                                'type': 'DIVIDEND',
                                'symbol': symbol,
                                'qty': Decimal('0'),
                                'price': Decimal('0'),
                                'amount': amount
                            })
                        else:
                            transactions.append({
                                'date': tx_date,
                                'type': operation,
                                'symbol': symbol,
                                'qty': qty,
                                'price': price if price > 0 else (amount / qty if qty > 0 else Decimal('0')),
                                'amount': amount
                            })
                        
                        i = j + 1
                        continue
                    
                    # Check for symbol on separate line
                    if re.match(r'^[A-Z]{1,5}$', next_line):
                        symbol = next_line
                        if i + 2 < len(lines) and ('Trade' in lines[i + 2] or 'Dividend' in lines[i + 2]):
                            tx_type_line = lines[i + 2]
                            tx_type = 'DIVIDEND' if 'Dividend' in tx_type_line else 'TRADE'
                            
                            j = i + 3
                            qty = Decimal('0')
                            price = Decimal('0')
                            operation = 'BUY'
                            amount = Decimal('0')
                            
                            while j < len(lines) and j < i + 10:
                                check = lines[j]
                                qty_match = re.match(r'^([\d.]+)$', check)
                                if qty_match and qty == 0:
                                    qty = Decimal(qty_match.group(1))
                                    j += 1
                                    continue
                                if 'Buy' in check or 'Sell' in check:
                                    operation = 'BUY' if 'Buy' in check else 'SELL'
                                    amount = parse_usd_amount(check)
                                    break
                                if 'US$' in check and price == 0:
                                    price = parse_usd_amount(check)
                                j += 1
                            
                            if tx_type == 'DIVIDEND':
                                amount = parse_usd_amount(lines[i + 3]) if i + 3 < len(lines) else Decimal('0')
                                transactions.append({
                                    'date': tx_date,
                                    'type': 'DIVIDEND',
                                    'symbol': symbol,
                                    'qty': Decimal('0'),
                                    'price': Decimal('0'),
                                    'amount': amount
                                })
                            else:
                                transactions.append({
                                    'date': tx_date,
                                    'type': operation,
                                    'symbol': symbol,
                                    'qty': qty,
                                    'price': price if price > 0 else (amount / qty if qty > 0 else Decimal('0')),
                                    'amount': amount
                                })
                            
                            i = j + 1
                            continue
        
        i += 1
    
    # Insert holdings
    print(f"\n📥 Inserting {len(holdings)} holdings...")
    for h in holdings:
        try:
            holding = Holding(
                id=uuid.uuid4(),
                broker='REVOLUT',
                ticker=h['symbol'],
                isin=h['isin'],
                name=h['name'],
                asset_type='STOCK',
                quantity=h['quantity'],
                current_value=h['value'],
                current_price=h['price'],
                currency='USD',
                source_document=Path(pdf_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {e}")
    
    # Add cash holding
    if cash_balance > 0:
        cash_holding = Holding(
            id=uuid.uuid4(),
            broker='REVOLUT',
            ticker='USD_CASH',
            name='Cash (USD)',
            asset_type='CASH',
            quantity=cash_balance,
            current_value=cash_balance,
            current_price=Decimal('1'),
            purchase_price=Decimal('1'),
            currency='USD',
            source_document=Path(pdf_path).name,
            last_updated=datetime.now()
        )
        session.add(cash_holding)
        session.commit()
        print(f"  💵 Added USD CASH: ${cash_balance:.2f}")
    
    # Insert transactions
    trades = dividends = deposits = 0
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    for tx in transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='REVOLUT',
                ticker=tx['symbol'],
                operation=tx['type'] if tx['type'] in ['BUY', 'SELL', 'DIVIDEND'] else ('DEPOSIT' if tx['type'] == 'DEPOSIT' else 'WITHDRAWAL'),
                quantity=tx['qty'],
                price=tx['price'],
                total_amount=tx['amount'],
                currency='USD',
                fees=Decimal('0'),
                timestamp=tx['date'],
                source_document=Path(pdf_path).name
            )
            session.add(transaction)
            session.commit()
            
            if tx['type'] in ['BUY', 'SELL']:
                trades += 1
            elif tx['type'] == 'DIVIDEND':
                dividends += 1
            else:
                deposits += 1
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {str(e)[:50]}")
    
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Holdings: {len(holdings)}")
    print(f"  Cash:     ${cash_balance:.2f}")
    print(f"  Trades:   {trades}")
    print(f"  Dividends: {dividends}")
    print(f"  Deposits: {deposits}")
    print(f"=" * 70)
    
    return len(holdings) + len(transactions)


if __name__ == "__main__":
    pdf_path = r'D:\Download\Revolut\trading-account-statement_2019-12-28_2025-12-20_it-it_a927d3.pdf'
    parse_revolut_stocks(pdf_path)
