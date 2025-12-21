"""
Parse BG Saxo Holdings from CSV.
Extracts: current holdings with quantities, values, and prices.
Separate from transactions parser for clean separation of concerns.
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding


def find_bgsaxo_csv() -> Path:
    """Find BG Saxo holdings CSV file."""
    folder = Path(r'D:\Download\BGSAXO')
    
    # Look for files with 'Posizioni' or 'Holdings' in name
    holdings_files = (
        list(folder.glob('*Posizioni*.csv')) + 
        list(folder.glob('*Holdings*.csv')) + 
        list(folder.glob('*holdings*.csv'))
    )
    if holdings_files:
        return sorted(holdings_files)[-1]  # Most recent
    
    # Fall back to any CSV
    csv_files = list(folder.glob('*.csv'))
    if csv_files:
        return sorted(csv_files)[-1]
    
    raise FileNotFoundError(f"No CSV files found in {folder}")


def parse_european_number(value: str) -> Decimal:
    """Parse European number format (1.234,56) to Decimal."""
    if not value or value == '-':
        return Decimal('0')
    
    clean = value.strip()
    
    # Skip if already in US format (has . but no ,)
    if ',' not in clean and '.' in clean:
        try:
            return Decimal(clean)
        except InvalidOperation:
            return Decimal('0')
    
    # European format: replace . with nothing, , with .
    clean = clean.replace('.', '').replace(',', '.')
    
    try:
        return Decimal(clean)
    except InvalidOperation:
        return Decimal('0')


def safe_price(value: Decimal, quantity: Decimal) -> Decimal:
    """Calculate safe price, handling edge cases."""
    if quantity == 0 or value == 0:
        return Decimal('0')
    
    price = value / quantity
    
    # Cap to 4 decimal places and reasonable value
    price = round(price, 4)
    if price > Decimal('999999.9999'):
        price = Decimal('999999.9999')
    
    return price


def parse_bgsaxo_holdings(csv_path: str = None):
    """Parse BG Saxo CSV for holdings."""
    print("=" * 70)
    print("PARSING BG SAXO HOLDINGS")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Find CSV if not provided
    if csv_path is None:
        csv_path = find_bgsaxo_csv()
    
    print(f"File: {Path(csv_path).name}")
    
    # Clear existing BG Saxo holdings
    deleted = session.query(Holding).filter(Holding.broker == 'BG_SAXO').delete()
    session.commit()
    print(f"Cleared {deleted} existing BG_SAXO holdings")
    
    # Read CSV - use comma delimiter
    holdings = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=',')
        
        for row in reader:
            # Get name from Strumento column
            name = row.get('Strumento', row.get('Symbol', row.get('Instrument', '')))
            if not name or len(name.strip()) < 1:
                continue
            
            name = name.strip()
            
            # Skip cash/totals rows
            if name.lower() in ['totale', 'total', 'cash', 'contante', '']:
                continue
            
            # Parse values - columns may vary
            quantity_str = row.get('Quantità', row.get('Quantity', ''))
            if not quantity_str or quantity_str.strip() == '':
                continue  # Skip group headers like "Azioni (48)"
            
            quantity = parse_european_number(quantity_str)
            
            # Get ISIN (important for price lookup!)
            isin = row.get('ISIN', '').strip()
            
            # Get currency from Valuta column
            currency = row.get('Valuta', row.get('Currency', 'EUR')).strip().upper()
            if not currency:
                currency = 'EUR'
            
            # Get ticker from Ticker column (format: "ORCL:xnys" -> "ORCL")
            raw_ticker = row.get('Ticker', '').strip()
            if raw_ticker and ':' in raw_ticker:
                ticker = raw_ticker.split(':')[0].upper()
            elif raw_ticker:
                ticker = raw_ticker.upper()
            else:
                # Fallback: use first word of name
                ticker = name.split()[0][:10] if ' ' in name else name[:10]
            
            # Value column - already in EUR from "Valore di mercato (EUR)"
            value_str = row.get('Valore di mercato (EUR)', row.get('Valore Mkt', row.get('Value', '0')))
            value = parse_european_number(value_str)
            
            # Price is in original currency
            price = parse_european_number(row.get('Prz. corrente', row.get('Prezzo', row.get('Price', '0'))))
            purchase_price = parse_european_number(row.get('Prezzo di apertura', row.get('Prezzo medio', '0')))
            
            # Skip zero quantity
            if quantity <= 0:
                continue
            
            # Calculate price if not available
            if price == 0 and value > 0 and quantity > 0:
                price = safe_price(value, quantity)
            
            holdings.append({
                'ticker': ticker[:15],
                'isin': isin if isin else None,
                'name': name[:100],
                'currency': currency,
                'quantity': quantity,
                'value': value,
                'price': price,
                'purchase_price': purchase_price if purchase_price > 0 else price
            })
    
    # Insert holdings
    print(f"\nInserting {len(holdings)} holdings...")
    
    total_value = Decimal('0')
    
    for h in holdings:
        try:
            holding = Holding(
                id=uuid.uuid4(),
                broker='BG_SAXO',
                ticker=h['ticker'],
                isin=h['isin'],
                name=h['name'],
                asset_type='ETF' if 'ETF' in h['name'].upper() or 'UCITS' in h['name'].upper() else 'STOCK',
                quantity=h['quantity'],
                current_value=h['value'],  # Already in EUR from "Valore di mercato (EUR)"
                current_price=h['price'],  # In original currency
                purchase_price=h['purchase_price'],
                currency=h['currency'],  # Original currency (EUR, USD, DKK, CAD, etc.)
                source_document=Path(csv_path).name,
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
            total_value += h['value']
            print(f"  [OK] {h['ticker'][:25]:<25} | Qty: {h['quantity']:>10.2f} | Value: {h['value']:>10.2f}")
        except Exception as e:
            session.rollback()
            print(f"  [ERR] {h['ticker']}: {str(e)[:50]}")
    
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"SUMMARY")
    print(f"=" * 70)
    print(f"  Holdings:    {len(holdings)}")
    print(f"  Total Value: {total_value:,.2f}")
    print(f"=" * 70)
    
    return len(holdings)


if __name__ == "__main__":
    parse_bgsaxo_holdings()
