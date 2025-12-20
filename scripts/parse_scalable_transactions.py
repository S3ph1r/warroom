"""
Parse all Scalable Capital/Baader Bank PDF documents for transactions.
Extracts: purchases, sales, deposits, dividends from monthly statements.
Uses PyMuPDF (fitz) for text extraction.
Handles variable layouts across different time periods.
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


def parse_amount(value: str) -> Decimal:
    """Parse amount like '62.27' or '0.99' to Decimal."""
    if not value:
        return Decimal('0')
    # Remove currency symbols and whitespace
    clean = re.sub(r'[€EUR\s]', '', value).replace(',', '.').replace('-', '').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_date(date_str: str) -> datetime:
    """Parse date like '2022-12-20' to datetime."""
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d')
    except:
        return None


def extract_transactions_from_pdf(pdf_path: str) -> list:
    """Extract transactions from a single PDF file."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  ⚠️ Cannot open: {e}")
        return []
    
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    
    transactions = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for transaction types and get amount from PREVIOUS line
        # Pattern: Date, Date, Amount, Type, ProductName, ISIN, STK
        
        # Purchase pattern - Amount is AFTER Purchase line (e.g., "62.27 -")
        if line.lower() in ['purchase', 'kauf', 'acquisto']:
            # Amount is in NEXT line (i+1), format: "62.27 -"
            amount = Decimal('0')
            if i + 1 < len(lines):
                amount_line = lines[i + 1].strip()
                amount = parse_amount(amount_line.replace('-', ''))
            
            # Product name is line i+2
            product_line = lines[i + 2].strip() if i + 2 < len(lines) else ''
            
            # Find ISIN and STK in following lines
            isin = None
            qty = 0
            tx_date = None
            
            for k in range(max(0, i - 4), min(i + 6, len(lines))):
                pk = lines[k].strip()
                # Get date from earlier lines
                date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', pk)
                if date_match and not tx_date:
                    tx_date = parse_date(date_match.group(1))
                # Get ISIN
                isin_match = re.search(r'ISIN\s*([A-Z]{2}[A-Z0-9]{10})', pk)
                if isin_match:
                    isin = isin_match.group(1)
                # Get quantity
                stk_match = re.search(r'STK\s+(\d+)', pk)
                if stk_match:
                    qty = int(stk_match.group(1))
            
            if isin and qty > 0 and tx_date:
                transactions.append({
                    'date': tx_date,
                    'type': 'BUY',
                    'product': product_line[:50],
                    'isin': isin,
                    'qty': qty,
                    'amount': amount
                })
            i += 5
            continue
        
        # Sale pattern
        if line.lower() in ['sale', 'verkauf', 'vendita']:
            amount = Decimal('0')
            if i > 0:
                amount_line = lines[i - 1].strip()
                amount = parse_amount(amount_line)
            
            product_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
            
            isin = None
            qty = 0
            tx_date = None
            
            for k in range(max(0, i - 4), min(i + 6, len(lines))):
                pk = lines[k].strip()
                date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', pk)
                if date_match and not tx_date:
                    tx_date = parse_date(date_match.group(1))
                isin_match = re.search(r'ISIN\s*([A-Z]{2}[A-Z0-9]{10})', pk)
                if isin_match:
                    isin = isin_match.group(1)
                stk_match = re.search(r'STK\s+(\d+)', pk)
                if stk_match:
                    qty = int(stk_match.group(1))
            
            if isin and qty > 0 and tx_date:
                transactions.append({
                    'date': tx_date,
                    'type': 'SELL',
                    'product': product_line[:50],
                    'isin': isin,
                    'qty': qty,
                    'amount': amount
                })
            i += 5
            continue
        
        # Dividend pattern (Coupons/Dividends)
        if 'coupons/dividends' in line.lower() or 'dividende' in line.lower() or 'ausschüttung' in line.lower():
            amount = Decimal('0')
            if i > 0:
                amount_line = lines[i - 1].strip()
                amount = parse_amount(amount_line)
            
            product_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
            
            isin = None
            tx_date = None
            
            for k in range(max(0, i - 4), min(i + 6, len(lines))):
                pk = lines[k].strip()
                date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', pk)
                if date_match and not tx_date:
                    tx_date = parse_date(date_match.group(1))
                isin_match = re.search(r'ISIN\s*([A-Z]{2}[A-Z0-9]{10})', pk)
                if isin_match:
                    isin = isin_match.group(1)
                    break
            
            if tx_date and amount > 0:
                transactions.append({
                    'date': tx_date,
                    'type': 'DIVIDEND',
                    'product': product_line[:50],
                    'isin': isin,
                    'qty': 0,
                    'amount': amount
                })
            i += 4
            continue
        
        # Deposit pattern (Direct Debit)
        if 'direct debit' in line.lower() or 'überweisung' in line.lower():
            # Look for amount in previous lines (usually 2-3 lines back after dates)
            amount = Decimal('0')
            tx_date = None
            
            for k in range(max(0, i - 5), i):
                pk = lines[k].strip()
                date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', pk)
                if date_match and not tx_date:
                    tx_date = parse_date(date_match.group(1))
                # Look for standalone amount
                amount_match = re.match(r'^(\d+[.,]\d{2})$', pk)
                if amount_match:
                    amount = parse_amount(amount_match.group(1))
            
            if tx_date and amount > 0:
                transactions.append({
                    'date': tx_date,
                    'type': 'DEPOSIT',
                    'product': 'Cash Deposit',
                    'isin': None,
                    'qty': 0,
                    'amount': amount
                })
            i += 5
            continue
        
        i += 1
    
    return transactions


def parse_all_scalable_transactions():
    """Parse all Scalable Capital PDF documents for transactions."""
    print("=" * 70)
    print("📊 PARSING SCALABLE CAPITAL TRANSACTIONS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Scalable transactions
    deleted = session.query(Transaction).filter(Transaction.broker == 'SCALABLE').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted} existing SCALABLE transactions")
    
    # Find all relevant PDFs
    scalable_folder = Path(r'D:\Download\SCALABLE CAPITAL')
    
    # Focus on Monthly account statement (Baader Bank and Scalable Capital)
    pdf_files = sorted(scalable_folder.glob('*Monthly account statement*.pdf'))
    
    print(f"\n📁 Found {len(pdf_files)} Monthly statement PDFs")
    
    all_transactions = []
    files_with_tx = 0
    
    for pdf_path in pdf_files:
        filename = pdf_path.name
        transactions = extract_transactions_from_pdf(str(pdf_path))
        
        if transactions:
            files_with_tx += 1
            all_transactions.extend(transactions)
            print(f"  ✅ {filename}: {len(transactions)} transactions")
            for tx in transactions:
                print(f"      {tx['date'].strftime('%Y-%m-%d')} | {tx['type']:<8} | {tx['product'][:25]:<25} | Qty: {tx['qty']:>4} | €{tx['amount']:>10.2f}")
        else:
            print(f"  ⏭️ {filename}: no transactions")
    
    # Insert transactions
    print(f"\n📥 Inserting {len(all_transactions)} transactions...")
    
    buys = sells = dividends = deposits = 0
    
    for tx in all_transactions:
        try:
            transaction = Transaction(
                id=uuid.uuid4(),
                broker='SCALABLE',
                ticker=tx['isin'] or 'EUR_CASH',
                isin=tx.get('isin'),
                operation=tx['type'],
                quantity=Decimal(str(tx['qty'])) if tx['qty'] > 0 else tx['amount'],
                price=tx['amount'] / tx['qty'] if tx['qty'] > 0 else Decimal('1'),
                total_amount=tx['amount'],
                currency='EUR',
                fees=Decimal('0'),
                timestamp=tx['date'],
                source_document=f"Scalable Monthly Statement",
                notes=tx['product'][:100]
            )
            session.add(transaction)
            session.commit()
            
            if tx['type'] == 'BUY':
                buys += 1
            elif tx['type'] == 'SELL':
                sells += 1
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
    print(f"  PDF files with transactions: {files_with_tx}")
    print(f"  Buys:      {buys}")
    print(f"  Sells:     {sells}")
    print(f"  Dividends: {dividends}")
    print(f"  Deposits:  {deposits}")
    print(f"  TOTAL:     {len(all_transactions)}")
    print(f"=" * 70)
    
    return len(all_transactions)


if __name__ == "__main__":
    parse_all_scalable_transactions()
