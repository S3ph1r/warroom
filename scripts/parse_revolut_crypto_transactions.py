"""
Parse Revolut Crypto Account Statement PDF for transactions.
Extracts: crypto transactions (buys, sells, staking rewards).
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
from db.models import Transaction


def parse_euro_amount(value: str) -> Decimal:
    """Parse Euro amount like '49,00€' or '1.680,85€' to Decimal."""
    if not value:
        return Decimal('0')
    # Remove € and handle European format (1.234,56)
    clean = value.replace('€', '').replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_crypto_qty(value: str) -> Decimal:
    """Parse crypto quantity like '431,3846815' to Decimal."""
    if not value:
        return Decimal('0')
    clean = value.replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_italian_date(date_str: str) -> datetime:
    """Parse Italian date like '22 lug 2022, 14:54:25' to datetime."""
    months = {
        'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
        'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
    }
    try:
        # Pattern: "22 lug 2022, 14:54:25"
        match = re.match(r'(\d+)\s+(\w+)\s+(\d{4}),\s+(\d{2}):(\d{2}):(\d{2})', date_str)
        if match:
            day = int(match.group(1))
            month = months.get(match.group(2).lower(), 1)
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            return datetime(year, month, day, hour, minute, second)
    except:
        pass
    return None


def parse_revolut_crypto_transactions(pdf_path: str):
    """Parse Revolut Crypto PDF for transactions."""
    print("=" * 70)
    print("📊 PARSING REVOLUT CRYPTO TRANSACTIONS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Revolut Crypto transactions (but keep holdings)
    deleted = session.query(Transaction).filter(
        Transaction.broker == 'REVOLUT',
        Transaction.currency == 'EUR',
        Transaction.ticker.notin_(['GOOGL', 'BIDU', 'BP', 'USD_CASH'])  # Keep stock transactions
    ).delete(synchronize_session=False)
    session.commit()
    print(f"🗑️  Cleared {deleted} existing REVOLUT crypto transactions")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()
    
    lines = [l.strip() for l in all_text.split('\n') if l.strip()]
    
    # Known crypto symbols
    crypto_symbols = ['POL', 'DOT', 'SOL', '1INCH', 'AVAX', 'MANA', 'MATIC', 'ETH', 
                      'SAND', 'XLM', 'BTC', 'GALA']
    
    # Transaction types
    tx_types = {
        'acquisto': 'BUY',
        'vendita': 'SELL',
        'invio': 'WITHDRAWAL',
        'staking': 'STAKING',
        'annullamento staking': 'UNSTAKING',
        'acquista - revolut x': 'BUY'
    }
    
    transactions = []
    i = 0
    in_transactions = False
    
    while i < len(lines):
        line = lines[i]
        
        # Detect transactions section
        if line == 'Transazioni':
            in_transactions = True
            i += 1
            continue
        
        # End of transactions section (staking rewards section)
        if 'Ricompense per lo staking' in line:
            in_transactions = False
            i += 1
            continue
        
        # Parse transactions
        if in_transactions and line in crypto_symbols:
            symbol = line
            
            # Check if next line is a transaction type
            if i + 6 < len(lines):
                type_line = lines[i + 1].lower()
                
                op_type = None
                for key, value in tx_types.items():
                    if key in type_line:
                        op_type = value
                        break
                
                if op_type:
                    qty = parse_crypto_qty(lines[i + 2])
                    price = parse_euro_amount(lines[i + 3])
                    value = parse_euro_amount(lines[i + 4])
                    fees = parse_euro_amount(lines[i + 5])
                    tx_date = parse_italian_date(lines[i + 6])
                    
                    if tx_date:
                        transactions.append({
                            'date': tx_date,
                            'type': op_type,
                            'symbol': symbol,
                            'qty': qty,
                            'price': price,
                            'value': value,
                            'fees': fees
                        })
                        print(f"  {tx_date.strftime('%Y-%m-%d')} | {op_type:<8} | {symbol:<6} | Qty: {qty:>15.6f} | €{value:>10.2f}")
                    
                    i += 7
                    continue
        
        i += 1
    
    # Insert transactions
    print(f"\n📥 Inserting {len(transactions)} transactions...")
    
    buys = sells = other = 0
    total_fees = Decimal('0')
    
    for tx in transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='REVOLUT',
                ticker=tx['symbol'],
                operation=tx['type'],
                quantity=tx['qty'],
                price=tx['price'],
                total_amount=tx['value'],
                currency='EUR',
                fees=tx['fees'],
                timestamp=tx['date'],
                source_document=Path(pdf_path).name
            )
            session.add(transaction)
            session.commit()
            
            if tx['type'] == 'BUY':
                buys += 1
            elif tx['type'] == 'SELL':
                sells += 1
            else:
                other += 1
            total_fees += tx['fees']
            
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {str(e)[:50]}")
    
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Buys:     {buys}")
    print(f"  Sells:    {sells}")
    print(f"  Other:    {other}")
    print(f"  TOTAL:    {len(transactions)}")
    print(f"  Fees:     €{total_fees:.2f}")
    print(f"=" * 70)
    
    return len(transactions)


if __name__ == "__main__":
    pdf_path = r'D:\Download\Revolut\crypto-account-statement_2022-07-04_2025-12-20_it-it_1c330c.pdf'
    parse_revolut_crypto_transactions(pdf_path)
