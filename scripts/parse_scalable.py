"""
Parse Scalable Capital Financial Status PDF.
Extracts: holdings (ETFs + stocks) and cash balance.
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
from db.models import Holding


def parse_euro_amount(value: str) -> Decimal:
    """Parse amount like '4,146.80 EUR' or '17.56 EUR' to Decimal."""
    if not value:
        return Decimal('0')
    # Format: 4,146.80 or 17.56 (English format with comma as thousands separator)
    clean = value.replace('EUR', '').replace(',', '').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_scalable_financial_status(pdf_path: str):
    """Parse Scalable Capital Financial Status PDF."""
    print("=" * 70)
    print("📊 PARSING SCALABLE CAPITAL FINANCIAL STATUS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Scalable holdings
    deleted = session.query(Holding).filter(Holding.broker == 'SCALABLE').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted} existing SCALABLE holdings")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()
    
    lines = [l.strip() for l in all_text.split('\n') if l.strip()]
    
    # Find cash balance (Saldo row in Panoramica section)
    cash_balance = Decimal('0')
    holdings = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for "Saldo" section for cash
        if line == 'Saldo' and i + 1 < len(lines):
            # Check if next line is a percentage (0,00 %)
            next_line = lines[i + 1]
            if '%' in next_line and i + 2 < len(lines):
                cash_line = lines[i + 2]
                if 'EUR' in cash_line:
                    cash_balance = parse_euro_amount(cash_line)
                    print(f"  💶 Cash Balance: €{cash_balance:.2f}")
            i += 3
            continue
        
        # Look for holdings pattern: Qty on one line, then Name, then ISIN, then Value
        # Pattern: number.0 followed by name followed by ISIN followed by value
        qty_match = re.match(r'^(\d+)\.0$', line)
        if qty_match:
            qty = int(qty_match.group(1))
            
            # Next lines should be: Name, ISIN, Value EUR
            if i + 3 < len(lines):
                name = lines[i + 1]
                isin = lines[i + 2]
                value_line = lines[i + 3]
                
                # Validate ISIN format
                if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', isin):
                    value = parse_euro_amount(value_line)
                    
                    # Determine asset type
                    asset_type = 'STOCK'
                    if 'iShares' in name or 'ETF' in name or 'L&G' in name:
                        asset_type = 'ETF'
                    
                    holding = {
                        'ticker': isin,  # Use ISIN as ticker
                        'name': name[:50],
                        'isin': isin,
                        'quantity': qty,
                        'value': value,
                        'asset_type': asset_type
                    }
                    holdings.append(holding)
                    print(f"  📊 {qty:>4} | {name[:30]:<30} | {isin} | €{value:>10.2f}")
                    
                    i += 4
                    continue
        
        i += 1
    
    # Insert holdings into database
    print(f"\n📥 Inserting {len(holdings)} holdings...")
    
    for h in holdings:
        try:
            price_per_unit = h['value'] / h['quantity'] if h['quantity'] > 0 else Decimal('0')
            
            holding = Holding(
                id=uuid.uuid4(),
                broker='SCALABLE',
                ticker=h['ticker'],
                isin=h['isin'],
                name=h['name'],
                asset_type=h['asset_type'],
                quantity=Decimal(str(h['quantity'])),
                current_value=h['value'],
                current_price=price_per_unit,
                currency='EUR',
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
            broker='SCALABLE',
            ticker='CASH',
            name='Cash (EUR)',
            asset_type='CASH',
            quantity=cash_balance,
            current_value=cash_balance,
            current_price=Decimal('1'),
            purchase_price=Decimal('1'),
            currency='EUR',
            source_document=Path(pdf_path).name,
            last_updated=datetime.now()
        )
        session.add(cash_holding)
        session.commit()
        print(f"  💶 Added CASH holding: €{cash_balance:.2f}")
    
    session.close()
    
    # Summary
    total_value = sum(h['value'] for h in holdings) + cash_balance
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  ETFs:    {sum(1 for h in holdings if h['asset_type'] == 'ETF')}")
    print(f"  Stocks:  {sum(1 for h in holdings if h['asset_type'] == 'STOCK')}")
    print(f"  Cash:    €{cash_balance:.2f}")
    print(f"  TOTAL:   €{total_value:.2f}")
    print(f"=" * 70)
    
    return len(holdings) + (1 if cash_balance > 0 else 0)


if __name__ == "__main__":
    pdf_path = r'D:\Download\SCALABLE CAPITAL\20251219 Financial status Scalable Capital.pdf'
    parse_scalable_financial_status(pdf_path)
