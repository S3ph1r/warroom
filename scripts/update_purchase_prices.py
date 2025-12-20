"""
Update Holdings with Purchase Prices and Populate Transactions
1. Updates BG Saxo holdings with purchase price and P&L from CSV
2. Parses IBKR transactions CSV and inserts into transactions table
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction


def parse_number(value: str) -> Decimal:
    """Parse number from string, handling both US and EU formats."""
    if not value or value == '' or value == '-':
        return Decimal('0')
    
    clean = str(value).replace(' EUR', '').replace(' USD', '').strip()
    
    has_comma = ',' in clean
    has_dot = '.' in clean
    
    if has_comma and has_dot:
        last_comma = clean.rfind(',')
        last_dot = clean.rfind('.')
        
        if last_comma > last_dot:
            clean = clean.replace('.', '').replace(',', '.')
        else:
            clean = clean.replace(',', '')
    elif has_comma:
        clean = clean.replace(',', '.')
    
    try:
        return Decimal(clean)
    except:
        return Decimal('0')


def safe_price(value: Decimal, quantity: Decimal) -> Decimal:
    """Calculate price with safe bounds for DECIMAL(18,4)."""
    if quantity == 0:
        return Decimal('0')
    price = value / quantity
    price = price.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    max_price = Decimal('999999999')
    if price > max_price:
        price = max_price
    return price


def update_bgsaxo_with_purchase_prices():
    """Update BG Saxo holdings with purchase price and P&L from CSV."""
    session = SessionLocal()
    csv_path = r'D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv'
    
    print("=" * 70)
    print("📊 UPDATING BG SAXO WITH PURCHASE PRICES")
    print("=" * 70)
    
    updated = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            strumento = row.get('Strumento', '').strip()
            
            # Skip header rows
            if not strumento or strumento.startswith('Azioni (') or strumento.startswith('ETP ('):
                continue
            
            ticker = row.get('Ticker', '').strip()
            if ':' in ticker:
                ticker = ticker.split(':')[0]
            
            # Get purchase price (Prezzo di apertura)
            prezzo_apertura = parse_number(row.get('Prezzo di apertura', '0'))
            valore_originale = parse_number(row.get('Valore originale (EUR)', '0'))
            pnl_netto = parse_number(row.get('P&L netto EUR', '0'))
            
            if ticker:
                # Find the holding
                holding = session.query(Holding).filter(
                    Holding.broker == 'BG_SAXO',
                    Holding.ticker == ticker
                ).first()
                
                if holding and prezzo_apertura > 0:
                    holding.purchase_price = prezzo_apertura
                    # Note: we could also add invested_amount to the model
                    print(f"  ✅ {ticker:<12} | Prezzo acquisto: €{prezzo_apertura:>8.2f} | P&L: €{pnl_netto:>8.2f}")
                    updated += 1
    
    session.commit()
    session.close()
    
    print(f"\n✅ Updated {updated} BG Saxo holdings with purchase prices")
    return updated


def parse_ibkr_transactions():
    """Parse IBKR transactions CSV and insert into database."""
    session = SessionLocal()
    csv_path = r'D:\Download\IBKR\U22156212.TRANSACTIONS.1Y.csv'
    
    print("\n" + "=" * 70)
    print("📊 PARSING IBKR TRANSACTIONS")
    print("=" * 70)
    
    # Clear existing IBKR transactions
    deleted = session.query(Transaction).filter(Transaction.broker == 'IBKR').delete()
    session.commit()
    print(f"🗑️  Cleared {deleted} existing IBKR transactions")
    
    inserted = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        
        for row in reader:
            # Transaction History rows have 12 columns and start with specific values
            if len(row) >= 12 and row[0] == 'Transaction History' and row[1] == 'Data':
                date_str = row[2]
                account = row[3]
                description = row[4]
                tx_type = row[5]
                symbol = row[6]
                quantity = parse_number(row[7])
                price = parse_number(row[8])
                gross_amount = parse_number(row[9])
                commission = parse_number(row[10])
                net_amount = parse_number(row[11])
                
                # Skip Forex components and adjustments
                if 'Forex' in tx_type or 'Adjustment' in tx_type:
                    continue
                if symbol == '-' or symbol == 'EUR.USD':
                    # Check if it's a deposit
                    if 'Trasferimento' in description or 'Deposit' in tx_type:
                        symbol = 'EUR'
                        tx_type = 'DEPOSIT'
                        quantity = abs(net_amount)
                        price = Decimal('1')
                    else:
                        continue
                
                # Determine operation type
                operation = 'BUY'
                if tx_type == 'Sell':
                    operation = 'SELL'
                elif tx_type == 'DEPOSIT':
                    operation = 'DEPOSIT'
                
                # Parse date
                try:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    continue
                
                # Create transaction
                tx = Transaction(
                    id=uuid.uuid4(),
                    broker='IBKR',
                    ticker=symbol,
                    isin=None,
                    operation=operation,
                    quantity=abs(quantity),
                    price=abs(price),
                    total_amount=abs(net_amount),
                    currency='EUR',
                    fees=abs(commission),
                    timestamp=timestamp,
                    source_document='U22156212.TRANSACTIONS.1Y.csv',
                    notes=description[:100] if description else None
                )
                
                session.add(tx)
                inserted += 1
                print(f"  📝 {date_str} | {operation:<8} | {symbol:<8} | Qty: {abs(quantity):>6.2f} | €{abs(net_amount):>10.2f}")
    
    session.commit()
    session.close()
    
    print(f"\n✅ Inserted {inserted} IBKR transactions")
    return inserted



def show_summary():
    """Show summary of holdings and transactions."""
    session = SessionLocal()
    
    print("\n" + "=" * 70)
    print("📊 DATABASE SUMMARY")
    print("=" * 70)
    
    # Holdings with purchase price
    holdings_with_price = session.query(Holding).filter(Holding.purchase_price != None).count()
    holdings_total = session.query(Holding).count()
    
    print(f"\n📈 Holdings: {holdings_total} total, {holdings_with_price} with purchase price")
    
    # Transactions by broker
    from sqlalchemy import func
    tx_counts = session.query(
        Transaction.broker,
        func.count(Transaction.id),
        func.sum(Transaction.total_amount)
    ).group_by(Transaction.broker).all()
    
    print(f"\n📝 Transactions:")
    for broker, count, total in tx_counts:
        print(f"   {broker}: {count} transactions, €{total:,.2f}")
    
    session.close()


if __name__ == "__main__":
    update_bgsaxo_with_purchase_prices()
    parse_ibkr_transactions()
    show_summary()
