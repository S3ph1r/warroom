"""
Parse Revolut Crypto Account Statement PDF.
Extracts: crypto holdings and transactions.
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


def parse_euro_amount(value: str) -> Decimal:
    """Parse Euro amount like '12,69€' or '0,67€' to Decimal."""
    if not value:
        return Decimal('0')
    clean = value.replace('€', '').replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_crypto_qty(value: str) -> Decimal:
    """Parse crypto quantity like '136,6432338' to Decimal."""
    if not value:
        return Decimal('0')
    clean = value.replace('.', '').replace(',', '.').strip()
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def parse_revolut_crypto(pdf_path: str):
    """Parse Revolut Crypto Account Statement PDF."""
    print("=" * 70)
    print("📊 PARSING REVOLUT CRYPTO")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Clear existing Revolut Crypto holdings and transactions
    deleted_h = session.query(Holding).filter(
        Holding.broker == 'REVOLUT',
        Holding.asset_type == 'CRYPTO'
    ).delete(synchronize_session=False)
    deleted_t = session.query(Transaction).filter(
        Transaction.broker == 'REVOLUT',
        Transaction.currency == 'EUR',
        Transaction.ticker.notin_(['GOOGL', 'BIDU', 'BP', 'USD_CASH'])
    ).delete(synchronize_session=False)
    session.commit()
    print(f"🗑️  Cleared {deleted_h} REVOLUT crypto holdings")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    all_text = ""
    for page in doc:
        all_text += page.get_text() + "\n"
    doc.close()
    
    lines = [l.strip() for l in all_text.split('\n') if l.strip()]
    
    # Holdings from "Analisi dettagliata del portafoglio" section
    # Format: Symbol, Asset Name, Quantity, Price, Value, % of Portfolio
    holdings = []
    
    # Known crypto symbols
    crypto_symbols = ['POL', 'DOT', 'SOL', '1INCH', 'AVAX', 'MANA', 'MATIC', 'ETH', 'SAND', 'XLM', 'BTC', 'GALA']
    
    i = 0
    in_portfolio = False
    
    while i < len(lines):
        line = lines[i]
        
        # Detect portfolio section
        if 'Analisi dettagliata del portafoglio' in line:
            in_portfolio = True
            i += 1
            continue
        
        # End of portfolio section
        if in_portfolio and 'Valore Crypto' in line:
            in_portfolio = False
            i += 1
            continue
        
        # Parse holdings in portfolio section
        if in_portfolio and line in crypto_symbols:
            symbol = line
            if i + 4 < len(lines):
                name = lines[i + 1]
                qty = lines[i + 2]
                price = lines[i + 3]
                value = lines[i + 4]
                
                # Parse values
                quantity = parse_crypto_qty(qty)
                current_price = parse_euro_amount(price)
                current_value = parse_euro_amount(value)
                
                if current_value > 0:  # Only include holdings with value
                    holdings.append({
                        'symbol': symbol,
                        'name': name[:50],
                        'quantity': quantity,
                        'price': current_price,
                        'value': current_value
                    })
                    print(f"  🪙 {symbol:<6} | {name[:20]:<20} | Qty: {quantity:>15} | €{current_value:>8.2f}")
                
                i += 5
                continue
        
        i += 1
    
    # Insert holdings
    print(f"\n📥 Inserting {len(holdings)} crypto holdings...")
    for h in holdings:
        try:
            holding = Holding(
                id=uuid.uuid4(),
                broker='REVOLUT',
                ticker=h['symbol'],
                name=h['name'],
                asset_type='CRYPTO',
                quantity=h['quantity'],
                current_value=h['value'],
                current_price=h['price'],
                currency='EUR',
                source_document=Path(pdf_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"  ⚠️ Error: {e}")
    
    session.close()
    
    total_value = sum(h['value'] for h in holdings)
    print(f"\n" + "=" * 70)
    print(f"📊 SUMMARY")
    print(f"=" * 70)
    print(f"  Crypto Holdings: {len(holdings)}")
    print(f"  Total Value:     €{total_value:.2f}")
    print(f"=" * 70)
    
    return len(holdings)


if __name__ == "__main__":
    pdf_path = r'D:\Download\Revolut\crypto-account-statement_2022-07-04_2025-12-20_it-it_1c330c.pdf'
    parse_revolut_crypto(pdf_path)
