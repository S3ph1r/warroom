"""
Parse BG Saxo Transactions PDF and insert into database.
Extracts: trades (buy/sell), dividends, deposits, and final cash balance.
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
from db.models import Transaction, Holding


# Month mapping Italian to number
MONTH_MAP = {
    'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
    'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
}


def parse_italian_date(date_str: str) -> datetime:
    """Parse Italian date like '18-dic-2025' to datetime."""
    match = re.match(r'(\d{1,2})-(\w+)-(\d{4})', date_str)
    if match:
        day = int(match.group(1))
        month = MONTH_MAP.get(match.group(2).lower(), 1)
        year = int(match.group(3))
        return datetime(year, month, day)
    return None


def parse_euro_amount(value: str) -> Decimal:
    """Parse amount like '-1.170,68' or '1.362,01' to Decimal."""
    if not value or value == '-':
        return Decimal('0')
    # European format: 1.234,56
    clean = value.replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_bgsaxo_transactions(pdf_path: str):
    """Parse BG Saxo Transactions PDF."""
    print("=" * 70)
    print("📊 PARSING BG SAXO TRANSACTIONS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing BG_SAXO transactions
    deleted = session.query(Transaction).filter(Transaction.broker == 'BG_SAXO').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted} existing BG_SAXO transactions")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()
    
    lines = all_text.split('\n')
    
    transactions = []
    current_date = None
    current_cash = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for date line (e.g., "18-dic-2025")
        date_match = re.match(r'^(\d{1,2}-\w+-\d{4})$', line)
        if date_match:
            current_date = parse_italian_date(date_match.group(1))
            # Next two lines might be daily totals and cash balance
            if i + 2 < len(lines):
                # Check if next lines are numeric (amounts)
                next1 = lines[i + 1].strip()
                next2 = lines[i + 2].strip()
                if re.match(r'^-?[\d.,]+$', next1) and re.match(r'^[\d.,]+$', next2):
                    current_cash = parse_euro_amount(next2)
                    i += 3
                    continue
            i += 1
            continue
        
        # Check for trade: "Contrattazione" followed by product name
        if line == 'Contrattazione' and i + 1 < len(lines):
            product_name = lines[i + 1].strip()
            
            # Find the operation line (Acquista/Vendi X @ Prezzo)
            j = i + 2
            operation = None
            qty = 0
            price = Decimal('0')
            currency = 'EUR'
            amount = Decimal('0')
            commission = Decimal('0')
            isin = None
            trade_id = None
            
            while j < len(lines) and j < i + 25:  # Look within next 25 lines
                check_line = lines[j].strip()
                
                # Operation line: "Acquista 2 @ 301,93" or "Vendi -145 @ 2,90 CAD"
                op_match = re.match(r'^(Acquista|Vendi)\s+(-?\d+)\s+@\s+([\d.,]+)\s*(\w*)$', check_line)
                if op_match:
                    operation = 'BUY' if op_match.group(1) == 'Acquista' else 'SELL'
                    qty = abs(int(op_match.group(2)))
                    price = parse_euro_amount(op_match.group(3))
                    if op_match.group(4):
                        currency = op_match.group(4)
                    j += 1
                    continue
                
                # Amount line (negative for buy, positive for sell)
                amount_match = re.match(r'^(-?[\d.,]+)$', check_line)
                if amount_match and operation and amount == 0:
                    amount = parse_euro_amount(amount_match.group(1))
                    j += 1
                    continue
                
                # Commission line
                if check_line.startswith('Commissione'):
                    j += 1
                    if j < len(lines):
                        comm_match = re.match(r'^(-?[\d.,]+)\s*EUR$', lines[j].strip())
                        if comm_match:
                            commission = abs(parse_euro_amount(comm_match.group(1)))
                    j += 1
                    continue
                
                # Trade ID
                if check_line == 'ID contrattazione':
                    j += 1
                    if j < len(lines):
                        trade_id = lines[j].strip()
                    j += 1
                    continue
                
                # ISIN
                if check_line == 'ISIN':
                    j += 1
                    if j < len(lines):
                        isin = lines[j].strip()
                    break  # ISIN is usually last, stop here
                
                # New transaction or page break
                if check_line in ['Contrattazione', 'Operazione sul capitale', 'Trasferimento di liquidità'] or re.match(r'^\d{1,2}-\w+-\d{4}$', check_line):
                    break
                
                j += 1
            
            if operation and current_date and qty > 0:
                tx = {
                    'date': current_date,
                    'type': 'TRADE',
                    'operation': operation,
                    'product': product_name[:50],
                    'qty': qty,
                    'price': price,
                    'currency': currency,
                    'amount': abs(amount),
                    'commission': commission,
                    'isin': isin,
                    'trade_id': trade_id
                }
                transactions.append(tx)
                print(f"  📝 {current_date.strftime('%Y-%m-%d')} | {operation:<6} | {product_name[:25]:<25} | Qty: {qty:>4} | €{abs(amount):>10.2f}")
            
            i = j
            continue
        
        # Check for dividend: "Operazione sul capitale" + "Dividendo in contanti"
        if line == 'Operazione sul capitale' and i + 1 < len(lines):
            product_name = lines[i + 1].strip()
            
            j = i + 2
            is_dividend = False
            amount = Decimal('0')
            isin = None
            
            while j < len(lines) and j < i + 20:
                check_line = lines[j].strip()
                
                if 'Dividendo in contanti' in check_line:
                    is_dividend = True
                    j += 1
                    if j < len(lines):
                        amount = parse_euro_amount(lines[j].strip())
                    j += 1
                    continue
                
                if check_line == 'ISIN':
                    j += 1
                    if j < len(lines):
                        isin = lines[j].strip()
                    break
                
                if check_line in ['Contrattazione', 'Operazione sul capitale', 'Trasferimento di liquidità'] or re.match(r'^\d{1,2}-\w+-\d{4}$', check_line):
                    break
                
                j += 1
            
            if is_dividend and current_date and amount > 0:
                tx = {
                    'date': current_date,
                    'type': 'DIVIDEND',
                    'operation': 'DIVIDEND',
                    'product': product_name[:50],
                    'qty': 0,
                    'price': Decimal('0'),
                    'currency': 'EUR',
                    'amount': amount,
                    'commission': Decimal('0'),
                    'isin': isin,
                    'trade_id': None
                }
                transactions.append(tx)
                print(f"  💰 {current_date.strftime('%Y-%m-%d')} | DIV    | {product_name[:25]:<25} | €{amount:>10.2f}")
            
            i = j
            continue
        
        # Check for deposit: "Trasferimento di liquidità" + "Deposito"
        if line == 'Trasferimento di liquidità' and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            
            if next_line == 'Deposito':
                j = i + 2
                amount = Decimal('0')
                
                while j < len(lines) and j < i + 10:
                    check_line = lines[j].strip()
                    amount_match = re.match(r'^([\d.,]+)$', check_line)
                    if amount_match:
                        amount = parse_euro_amount(amount_match.group(1))
                        break
                    j += 1
                
                if current_date and amount > 0:
                    tx = {
                        'date': current_date,
                        'type': 'DEPOSIT',
                        'operation': 'DEPOSIT',
                        'product': 'Cash Deposit',
                        'qty': 0,
                        'price': Decimal('1'),
                        'currency': 'EUR',
                        'amount': amount,
                        'commission': Decimal('0'),
                        'isin': None,
                        'trade_id': None
                    }
                    transactions.append(tx)
                    print(f"  💵 {current_date.strftime('%Y-%m-%d')} | DEPOSIT | €{amount:>10.2f}")
                
                i = j + 1
                continue
        
        i += 1
    
    # Insert transactions into database
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    
    trades = 0
    dividends = 0
    deposits = 0
    
    for tx in transactions:
        try:
            # Ensure ticker is never NULL
            ticker = tx.get('isin') or tx['product'][:12].upper().replace(' ', '_')
            # For deposits and dividends without ISIN, use operation type as ticker
            if tx['type'] == 'DEPOSIT':
                ticker = 'EUR_CASH'
            elif tx['type'] == 'DIVIDEND' and not tx.get('isin'):
                ticker = tx['product'][:12].upper().replace(' ', '_')
            
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='BG_SAXO',
                ticker=ticker,
                isin=tx.get('isin'),
                operation=tx['operation'],
                quantity=Decimal(str(tx['qty'])) if tx['qty'] > 0 else tx['amount'],
                price=tx['price'] if tx['price'] > 0 else Decimal('1'),
                total_amount=tx['amount'],
                currency=tx['currency'] or 'EUR',
                fees=tx['commission'],
                timestamp=tx['date'],
                source_document=Path(pdf_path).name,
                notes=tx['product'][:100]
            )
            session.add(transaction)
            session.commit()  # Commit each transaction individually
            
            if tx['type'] == 'TRADE':
                trades += 1
            elif tx['type'] == 'DIVIDEND':
                dividends += 1
            elif tx['type'] == 'DEPOSIT':
                deposits += 1
                
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error inserting {tx['product'][:20]}: {str(e)[:50]}")
    
    # Add/update cash holding
    if current_cash is not None and current_cash > 0:
        print(f"\n💶 Final cash balance: €{current_cash:.2f}")
        
        # Check if CASH holding exists
        cash_holding = session.query(Holding).filter(
            Holding.broker == 'BG_SAXO',
            Holding.ticker == 'CASH'
        ).first()
        
        if cash_holding:
            cash_holding.quantity = current_cash
            cash_holding.current_value = current_cash
        else:
            cash_holding = Holding(
                id=uuid.uuid4(),
                broker='BG_SAXO',
                ticker='CASH',
                name='Cash (EUR)',
                asset_type='CASH',
                quantity=current_cash,
                current_value=current_cash,
                current_price=Decimal('1'),
                purchase_price=Decimal('1'),
                currency='EUR',
                source_document=Path(pdf_path).name,
                last_updated=datetime.now()
            )
            session.add(cash_holding)
        
        session.commit()
    
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Trades:    {trades}")
    print(f"  Dividends: {dividends}")
    print(f"  Deposits:  {deposits}")
    print(f"  TOTAL:     {len(transactions)}")
    if current_cash:
        print(f"  Cash:      €{current_cash:.2f}")
    print(f"=" * 70)
    
    return len(transactions)


if __name__ == "__main__":
    pdf_path = r'D:\Download\BGSAXO\Transactions_19807401_2024-11-26_2025-12-19.pdf'
    parse_bgsaxo_transactions(pdf_path)
