"""
Parse Revolut Commodities (Gold XAU, Silver XAG)
================================================
Extracts gold and silver holdings from Revolut account statement.
Each commodity has its own page with "Estratto conto in XAU/XAG" header.
Closing balance is in "Saldo di chiusura" column or last value in Totale row.
"""
import sys
import re
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import uuid

import fitz

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding


def extract_closing_balance(text: str, commodity: str) -> Decimal:
    """Extract closing balance for a commodity from page text."""
    # The Totale row has: initial, out, in, closing
    # We need to find the closing balance (last value in the row)
    
    # Pattern: numbers followed by XAU or XAG
    pattern = rf'(\d+\.\d+)\s*{commodity}'
    matches = re.findall(pattern, text)
    
    if not matches:
        return Decimal('0')
    
    # For XAU: 0.191230 is the closing balance (from screenshot)
    # For XAG: 3.387456 is the closing balance
    
    # Look for the summary table pattern
    # The closing balance is typically the 4th occurrence or one of the higher values
    
    # Filter valid values (non-zero)
    valid_values = []
    for m in matches:
        try:
            val = Decimal(m)
            if val > Decimal('0.001'):  # Skip very small values (like fees)
                valid_values.append(val)
        except:
            pass
    
    if not valid_values:
        return Decimal('0')
    
    # The Totale row typically has: 0.000000, out, in, closing
    # Look for "Totale" section and get the last value there
    if 'Totale' in text:
        totale_idx = text.find('Totale')
        after_totale = text[totale_idx:totale_idx+300]
        totale_matches = re.findall(pattern, after_totale)
        if len(totale_matches) >= 4:
            # Fourth value in Totale row is closing balance
            try:
                return Decimal(totale_matches[3])
            except:
                pass
    
    # Fallback: use the largest unique value (likely the closing balance)
    # But filter out values that appear multiple times (likely intermediate values)
    from collections import Counter
    count = Counter(valid_values)
    # Get values that appear at most twice (closing and possibly in Totale row)
    candidates = [v for v, c in count.items() if c <= 2]
    
    if candidates:
        return max(candidates)  # Take the highest
    
    return max(valid_values) if valid_values else Decimal('0')


def parse_revolut_commodities():
    """Parse Revolut commodities statement for gold and silver."""
    print("=" * 70)
    print("PARSING REVOLUT COMMODITIES (Gold/Silver)")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Find the commodities PDF
    folder = Path(r'D:\Download\Revolut')
    commodity_files = list(folder.glob('account-statement_*_it-it_*.pdf'))
    
    # Filter for the one with XAU/XAG
    pdf_path = None
    for f in commodity_files:
        if 'trading' not in f.name.lower() and 'crypto' not in f.name.lower():
            try:
                doc = fitz.open(f)
                text = doc[0].get_text()
                if 'XAU' in text or 'XAG' in text:
                    pdf_path = f
                    doc.close()
                    break
                doc.close()
            except:
                pass
    
    if not pdf_path:
        print("  No commodities PDF found!")
        return 0
    
    print(f"  File: {pdf_path.name}")
    
    doc = fitz.open(pdf_path)
    commodities = []
    
    # Process each page
    for i, page in enumerate(doc):
        text = page.get_text()
        
        # Determine commodity type from header
        if 'Estratto conto in XAU' in text:
            commodity = 'XAU'
            name = 'Gold (XAU)'
            price_eur = Decimal('3660')  # Revolut gold price EUR/oz (higher than spot)
        elif 'Estratto conto in XAG' in text:
            commodity = 'XAG'
            name = 'Silver (XAG)'
            price_eur = Decimal('56')  # Revolut silver price EUR/oz (higher than spot)
        else:
            continue
        
        # Extract closing balance
        balance = extract_closing_balance(text, commodity)
        
        if balance > Decimal('0'):
            value = balance * price_eur
            commodities.append({
                'ticker': commodity,
                'name': name,
                'quantity': balance,
                'price': price_eur,
                'value': value,
                'asset_type': 'COMMODITY'
            })
            print(f"  Found: {name} - {balance:.6f} oz x EUR {price_eur}/oz = EUR {value:.2f}")
    
    doc.close()
    
    if not commodities:
        print("  No commodities found in document!")
        return 0
    
    # Delete existing Revolut commodities
    deleted = session.query(Holding).filter(
        Holding.broker == 'REVOLUT',
        Holding.asset_type == 'COMMODITY'
    ).delete()
    session.commit()
    print(f"  Cleared {deleted} existing commodities")
    
    total_value = Decimal('0')
    
    for c in commodities:
        holding = Holding(
            id=uuid.uuid4(),
            broker='REVOLUT',
            ticker=c['ticker'],
            name=c['name'],
            asset_type='COMMODITY',
            quantity=c['quantity'],
            current_value=c['value'],
            current_price=c['price'],
            purchase_price=c['price'],
            currency='EUR',
            source_document=pdf_path.name,
            last_updated=datetime.now()
        )
        session.add(holding)
        total_value += c['value']
        print(f"  [OK] {c['ticker']} | Qty: {c['quantity']:.6f} oz | Value: EUR {c['value']:.2f}")
    
    session.commit()
    session.close()
    
    print(f"\n  Total Commodities Value: EUR {total_value:.2f}")
    print(f"  Inserted {len(commodities)} commodities")
    return len(commodities)


if __name__ == "__main__":
    parse_revolut_commodities()
