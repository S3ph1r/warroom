"""
Parse Trade Republic Estratto Conto PDF - Fixed Version
Uses line-based parsing with correct patterns.
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


# ISIN to ticker mapping
ISIN_TICKER_MAP = {
    'NL0010273215': 'ASML',
    'IE000M7V94E1': 'NUCL',
    'DE0005313704': 'AFX',
    'KYG017191142': 'BABA',
    'NL0011585146': 'RACE',
    'KYG9830T1067': 'XIACY',
    'US68389X1054': 'ORCL',
    'IE00BYZK4552': 'RBOT',
    'FR0000121329': 'HO',
}

MONTH_MAP = {
    'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
    'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
}


def parse_euro_amount(value: str) -> Decimal:
    """Parse Euro amount like '742,50 €' or '1.374,01€' to Decimal."""
    if not value:
        return Decimal('0')
    # Replace non-breaking space and regular spaces
    clean = value.replace('\xa0', '').replace('€', '').replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_trade_republic_pdf(pdf_path: str):
    """Parse Trade Republic PDF and extract transactions."""
    print("=" * 70)
    print("📊 PARSING TRADE REPUBLIC TRANSACTIONS (v2)")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing TR transactions
    deleted = session.query(Transaction).filter(Transaction.broker == 'TRADE_REPUBLIC').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted} existing TRADE_REPUBLIC transactions")
    
    # Read text file (already extracted)
    text_path = Path(__file__).parent / 'tr_pdf_text.txt'
    
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    transactions = []
    current_date = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Parse date: "19 set" followed by "2024"
        date_match = re.match(r'^(\d{1,2})\s+(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s*$', line, re.I)
        if date_match and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            year_match = re.match(r'^(\d{4})$', next_line)
            if year_match:
                day = int(date_match.group(1))
                month = MONTH_MAP.get(date_match.group(2).lower(), 1)
                year = int(year_match.group(1))
                current_date = datetime(year, month, day)
                i += 2
                continue
        
        # Parse transaction: "Commercio Buy/Sell trade ISIN NAME, quantity: N"
        if line.startswith('Commercio Buy trade') or line.startswith('Commercio Sell trade'):
            operation = 'BUY' if 'Buy trade' in line else 'SELL'
            
            # Full description may span multiple lines
            full_desc = line
            j = i + 1
            
            # Check if next line continues the description (no € at end)
            while j < len(lines):
                next_line = lines[j].strip()
                # If line contains € or is empty, stop
                if '€' in next_line or not next_line:
                    break
                # If it looks like a continuation (has 'quantity:' or text)
                if 'quantity:' in next_line.lower() or (len(next_line) > 5 and not next_line[0].isdigit()):
                    full_desc += ' ' + next_line
                    j += 1
                else:
                    break
            
            # Extract ISIN
            isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', full_desc)
            isin = isin_match.group(1) if isin_match else None
            
            # Extract quantity
            qty_match = re.search(r'quantity:\s*(\d+)', full_desc, re.I)
            quantity = int(qty_match.group(1)) if qty_match else 1
            
            # Get ticker from ISIN map
            ticker = ISIN_TICKER_MAP.get(isin, isin[-6:] if isin else 'UNKNOWN')
            
            # Get amount (next non-empty line with €)
            amount = Decimal('0')
            while j < len(lines):
                amount_line = lines[j].strip()
                if '€' in amount_line:
                    amount = parse_euro_amount(amount_line)
                    break
                j += 1
            
            # Calculate unit price
            unit_price = amount / quantity if quantity > 0 else Decimal('0')
            
            if current_date and isin:
                tx = {
                    'date': current_date,
                    'operation': operation,
                    'isin': isin,
                    'ticker': ticker,
                    'quantity': quantity,
                    'amount': amount,
                    'unit_price': unit_price,
                    'description': full_desc[:100]
                }
                transactions.append(tx)
                print(f"  📝 {current_date.strftime('%Y-%m-%d')} | {operation:<6} | {ticker:<8} | Qty: {quantity:>3} | €{amount:>10.2f} | Unit: €{unit_price:.2f}")
            
            i = j + 1
            continue
        
        i += 1
    
    # Insert into database
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    
    for tx in transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='TRADE_REPUBLIC',
                ticker=tx['ticker'],
                isin=tx['isin'],
                operation=tx['operation'],
                quantity=Decimal(str(tx['quantity'])),
                price=tx['unit_price'],
                total_amount=tx['amount'],
                currency='EUR',
                fees=Decimal('1'),
                timestamp=tx['date'],
                source_document='Estratto conto.pdf',
                notes=tx['description'][:100]
            )
            session.add(transaction)
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            session.rollback()
    
    session.commit()
    
    # Create holdings from transactions
    print(f"\n📊 Creating holdings from transactions...")
    create_holdings_from_transactions(session)
    
    session.close()
    
    print(f"\n✅ Inserted {len(transactions)} Trade Republic transactions")
    return len(transactions)


def create_holdings_from_transactions(session):
    """Create holdings from buy/sell transactions (net positions)."""
    from collections import defaultdict
    
    # Clear existing TR holdings
    deleted = session.query(Holding).filter(Holding.broker == 'TRADE_REPUBLIC').delete()
    session.commit()
    print(f"  Cleared {deleted} existing TRADE_REPUBLIC holdings")
    
    # Get all TR transactions
    transactions = session.query(Transaction).filter(
        Transaction.broker == 'TRADE_REPUBLIC'
    ).all()
    
    # Calculate net positions
    positions = defaultdict(lambda: {
        'qty': Decimal('0'),
        'total_cost': Decimal('0'),
        'isin': None,
        'ticker': None
    })
    
    for tx in transactions:
        key = tx.ticker
        if tx.operation == 'BUY':
            positions[key]['qty'] += tx.quantity
            positions[key]['total_cost'] += tx.total_amount
        elif tx.operation == 'SELL':
            positions[key]['qty'] -= tx.quantity
            # Don't subtract from cost basis for sells
        
        positions[key]['ticker'] = tx.ticker
        positions[key]['isin'] = tx.isin
    
    # Create holdings for positive positions
    created = 0
    for ticker, data in positions.items():
        if data['qty'] > 0:
            avg_price = data['total_cost'] / data['qty'] if data['qty'] > 0 else Decimal('0')
            
            holding = Holding(
                id=uuid.uuid4(),
                broker='TRADE_REPUBLIC',
                ticker=data['ticker'],
                isin=data['isin'],
                name=data['ticker'],
                asset_type='STOCK',
                quantity=data['qty'],
                current_value=data['qty'] * avg_price,  # Estimate using purchase price
                current_price=avg_price,
                purchase_price=avg_price,
                currency='EUR',
                source_document='Estratto conto.pdf',
                last_updated=datetime.now()
            )
            session.add(holding)
            created += 1
            print(f"  [OK] {ticker:<8} | Qty: {data['qty']:>5} | Avg: EUR{avg_price:>8.2f}")
    
    # Extract and add cash balance from PDF summary
    pdf_path = Path(r'D:\Download\Trade Repubblic\Estratto conto.pdf')
    try:
        import fitz
        doc = fitz.open(pdf_path)
        first_page = doc[0].get_text()
        doc.close()
        
        # Look for "SALDO FINALE" pattern - last value in summary row for "Conto corrente"
        # Format: "7,90 €" at end of row
        saldo_match = re.search(r'Conto corrente.*?(\d+[.,]\d+)\s*€\s*$', first_page, re.MULTILINE | re.DOTALL)
        if saldo_match:
            cash_str = saldo_match.group(1).replace('.', '').replace(',', '.')
            cash_balance = Decimal(cash_str)
        else:
            # Fallback: look for pattern like "7,90 €" followed by "TRANSAZIONI"
            patterns = re.findall(r'(\d+[.,]\d+)\s*€', first_page)
            # The cash balance is typically the 4th value (after initial, in, out, final)
            if len(patterns) >= 4:
                cash_str = patterns[3].replace('.', '').replace(',', '.')
                cash_balance = Decimal(cash_str)
            else:
                cash_balance = Decimal('0')
        
        if cash_balance > 0:
            cash_holding = Holding(
                id=uuid.uuid4(),
                broker='TRADE_REPUBLIC',
                ticker='EUR_CASH',
                name='Euro Cash Balance',
                asset_type='CASH',
                quantity=cash_balance,
                current_value=cash_balance,
                current_price=Decimal('1'),
                currency='EUR',
                source_document='Estratto conto.pdf',
                last_updated=datetime.now()
            )
            session.add(cash_holding)
            print(f"  [OK] CASH     | EUR {cash_balance:>8.2f}")
            created += 1
    except Exception as e:
        print(f"  [WARN] Could not extract cash balance: {e}")
    
    session.commit()
    print(f"  Created {created} holdings from transactions")


if __name__ == "__main__":
    pdf_path = r'D:\Download\Trade Repubblic\Estratto conto.pdf'
    parse_trade_republic_pdf(pdf_path)
