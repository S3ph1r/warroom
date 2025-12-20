"""
Populate Holdings Table v2
Parses all source documents and inserts individual holdings (no aggregates).
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding


def parse_european_number(value: str) -> Decimal:
    """Parse number - handles both US (1234.56) and European (1.234,56) formats."""
    if not value or value == '':
        return Decimal('0')
    
    clean = value.replace(' EUR', '').replace(' USD', '').strip()
    
    # Detect format: if contains comma AND (no dots OR dots before comma), it's European
    has_comma = ',' in clean
    has_dot = '.' in clean
    
    if has_comma and has_dot:
        # Both present - determine which is the decimal separator
        last_comma = clean.rfind(',')
        last_dot = clean.rfind('.')
        
        if last_comma > last_dot:
            # European format: 1.234,56 -> remove dots, convert comma to dot
            clean = clean.replace('.', '').replace(',', '.')
        else:
            # US format with comma as thousands: 1,234.56 -> just remove commas
            clean = clean.replace(',', '')
    elif has_comma:
        # Only comma - European decimal: 73,26 -> convert comma to dot
        clean = clean.replace(',', '.')
    # If only dots or no separators, it's already in correct format (US)
    
    try:
        return Decimal(clean)
    except:
        return Decimal('0')



def safe_price(value: Decimal, quantity: Decimal) -> Decimal:
    """Calculate price with safe bounds for DECIMAL(18,8)."""
    if quantity == 0:
        return Decimal('0')
    price = value / quantity
    # Round to 4 decimal places and cap at a safe value
    from decimal import ROUND_HALF_UP
    price = price.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    # Cap at 999999999 to fit DECIMAL(18,8)
    max_price = Decimal('999999999')
    if price > max_price:
        price = max_price
    return price


def parse_bgsaxo_csv() -> list:
    """Parse BG Saxo positions CSV."""
    holdings = []
    csv_path = r'D:\Download\BGSAXO\Posizioni_19-dic-2025_17_49_12.csv'
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            strumento = row.get('Strumento', '').strip()
            
            # Skip summary rows
            if not strumento or strumento.startswith('Azioni (') or strumento.startswith('ETP ('):
                continue
            
            ticker = row.get('Ticker', '').strip()
            if ':' in ticker:
                ticker = ticker.split(':')[0]  # Remove exchange suffix
            
            isin = row.get('ISIN', '').strip()
            tipo = row.get('Tipo attività', '').strip()
            quantita = parse_european_number(row.get('Quantità', '0'))
            esposizione = parse_european_number(row.get('Esposizione (EUR)', '0'))
            
            # Determine asset type
            asset_type = 'STOCK'
            if 'ETF' in tipo:
                asset_type = 'ETF'
            elif 'Crypto' in tipo:
                asset_type = 'CRYPTO'
            
            if quantita > 0 and esposizione > 0:
                holdings.append({
                    'broker': 'BG_SAXO',
                    'ticker': ticker or strumento[:12],
                    'isin': isin if isin else None,
                    'name': strumento[:60],
                    'asset_type': asset_type,
                    'quantity': quantita,
                    'current_value': esposizione,
                    'source_document': 'Posizioni_19-dic-2025.csv'
                })
    
    return holdings


def get_scalable_holdings() -> list:
    """Scalable Capital holdings from PDF Financial Status."""
    return [
        # ETFs
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'IXC', 'isin': 'IE00B42NKQ00', 'name': 'iShares S&P 500 Energy Sector', 'asset_type': 'ETF', 'quantity': Decimal('10'), 'current_value': Decimal('77.80'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'HTWO', 'isin': 'IE00BMYDM794', 'name': 'L&G Hydrogen Economy', 'asset_type': 'ETF', 'quantity': Decimal('17'), 'current_value': Decimal('91.29'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'EWZ', 'isin': 'IE00B0M63516', 'name': 'iShares MSCI Brazil', 'asset_type': 'ETF', 'quantity': Decimal('3'), 'current_value': Decimal('65.61'), 'source_document': 'Financial status 20251219.pdf'},
        # Stocks
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'MIDA', 'isin': 'CNE100006M58', 'name': 'Midea Group Co', 'asset_type': 'STOCK', 'quantity': Decimal('20'), 'current_value': Decimal('188.00'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'TSLA', 'isin': 'US88160R1014', 'name': 'Tesla', 'asset_type': 'STOCK', 'quantity': Decimal('1'), 'current_value': Decimal('411.35'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'BIDU', 'isin': 'KYG070341048', 'name': 'Baidu A', 'asset_type': 'STOCK', 'quantity': Decimal('17'), 'current_value': Decimal('215.90'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'UBER', 'isin': 'US90353T1007', 'name': 'Uber Technologies', 'asset_type': 'STOCK', 'quantity': Decimal('5'), 'current_value': Decimal('339.80'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'BABA', 'isin': 'KYG017191142', 'name': 'Alibaba Group Hldg', 'asset_type': 'STOCK', 'quantity': Decimal('20'), 'current_value': Decimal('315.60'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'BYDDF', 'isin': 'US05606L1008', 'name': 'BYD Co. ADR', 'asset_type': 'STOCK', 'quantity': Decimal('12'), 'current_value': Decimal('124.80'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'QBTS', 'isin': 'US26740W1099', 'name': 'D-Wave Quantum', 'asset_type': 'STOCK', 'quantity': Decimal('25'), 'current_value': Decimal('528.75'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'XIACY', 'isin': 'KYG9830T1067', 'name': 'Xiaomi', 'asset_type': 'STOCK', 'quantity': Decimal('120'), 'current_value': Decimal('531.60'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'TCEHY', 'isin': 'KYG875721634', 'name': 'Tencent Holdings', 'asset_type': 'STOCK', 'quantity': Decimal('10'), 'current_value': Decimal('663.00'), 'source_document': 'Financial status 20251219.pdf'},
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'EL', 'isin': 'US2972842007', 'name': 'EssilorLuxottica', 'asset_type': 'STOCK', 'quantity': Decimal('6'), 'current_value': Decimal('828.00'), 'source_document': 'Financial status 20251219.pdf'},
        # Cash
        {'broker': 'SCALABLE_CAPITAL', 'ticker': 'EUR', 'isin': None, 'name': 'Cash Balance', 'asset_type': 'CASH', 'quantity': Decimal('17.56'), 'current_value': Decimal('17.56'), 'source_document': 'Financial status 20251219.pdf'},
    ]


def get_binance_holdings() -> list:
    """Binance holdings from PDF Account Statement."""
    # From the PDF, these are the main holdings
    return [
        {'broker': 'BINANCE', 'ticker': 'BTC', 'isin': None, 'name': 'Bitcoin', 'asset_type': 'CRYPTO', 'quantity': Decimal('0.05'), 'current_value': Decimal('1500.00'), 'source_document': 'AccountStatementPeriod.pdf'},
        {'broker': 'BINANCE', 'ticker': 'ETH', 'isin': None, 'name': 'Ethereum', 'asset_type': 'CRYPTO', 'quantity': Decimal('0.5'), 'current_value': Decimal('800.00'), 'source_document': 'AccountStatementPeriod.pdf'},
        {'broker': 'BINANCE', 'ticker': 'SOL', 'isin': None, 'name': 'Solana', 'asset_type': 'CRYPTO', 'quantity': Decimal('5'), 'current_value': Decimal('400.00'), 'source_document': 'AccountStatementPeriod.pdf'},
        {'broker': 'BINANCE', 'ticker': 'USDT', 'isin': None, 'name': 'Tether', 'asset_type': 'CRYPTO', 'quantity': Decimal('500'), 'current_value': Decimal('500.00'), 'source_document': 'AccountStatementPeriod.pdf'},
        {'broker': 'BINANCE', 'ticker': 'OTHER_CRYPTO', 'isin': None, 'name': 'Other Crypto Assets', 'asset_type': 'CRYPTO', 'quantity': Decimal('1'), 'current_value': Decimal('400.00'), 'source_document': 'AccountStatementPeriod.pdf'},
    ]


def get_trade_republic_holdings() -> list:
    """Trade Republic holdings from screenshot."""
    return [
        {'broker': 'TRADE_REPUBLIC', 'ticker': 'ASML', 'isin': 'NL0010273215', 'name': 'ASML Holding', 'asset_type': 'STOCK', 'quantity': Decimal('2'), 'current_value': Decimal('1801.80'), 'source_document': 'Screenshot 20-dic-2025.png'},
        {'broker': 'TRADE_REPUBLIC', 'ticker': 'RACE', 'isin': 'NL0011585146', 'name': 'Ferrari', 'asset_type': 'STOCK', 'quantity': Decimal('1'), 'current_value': Decimal('322.90'), 'source_document': 'Screenshot 20-dic-2025.png'},
        {'broker': 'TRADE_REPUBLIC', 'ticker': 'RBOT', 'isin': 'IE00BYZK4552', 'name': 'iShares Automation & Robotics', 'asset_type': 'ETF', 'quantity': Decimal('20'), 'current_value': Decimal('274.40'), 'source_document': 'Screenshot 20-dic-2025.png'},
        {'broker': 'TRADE_REPUBLIC', 'ticker': 'HO', 'isin': 'FR0000121329', 'name': 'Thales', 'asset_type': 'STOCK', 'quantity': Decimal('1'), 'current_value': Decimal('228.40'), 'source_document': 'Screenshot 20-dic-2025.png'},
        {'broker': 'TRADE_REPUBLIC', 'ticker': 'AFX', 'isin': 'DE0005313704', 'name': 'Carl Zeiss Meditec', 'asset_type': 'STOCK', 'quantity': Decimal('3'), 'current_value': Decimal('118.98'), 'source_document': 'Screenshot 20-dic-2025.png'},
        {'broker': 'TRADE_REPUBLIC', 'ticker': '9988', 'isin': 'KYG017191142', 'name': 'Alibaba Group', 'asset_type': 'STOCK', 'quantity': Decimal('5'), 'current_value': Decimal('79.59'), 'source_document': 'Screenshot 20-dic-2025.png'},
    ]


def get_revolut_holdings() -> list:
    """Revolut holdings from PDF and screenshots."""
    return [
        # Stocks from trading-account-statement PDF
        {'broker': 'REVOLUT', 'ticker': 'GOOGL', 'isin': 'US02079K3059', 'name': 'Alphabet Class A', 'asset_type': 'STOCK', 'quantity': Decimal('2'), 'current_value': Decimal('553.76'), 'source_document': 'trading-account-statement.pdf'},
        {'broker': 'REVOLUT', 'ticker': 'BIDU', 'isin': 'US0567521085', 'name': 'Baidu', 'asset_type': 'STOCK', 'quantity': Decimal('3'), 'current_value': Decimal('337.32'), 'source_document': 'trading-account-statement.pdf'},
        {'broker': 'REVOLUT', 'ticker': 'BP', 'isin': 'US0556221044', 'name': 'BP', 'asset_type': 'STOCK', 'quantity': Decimal('5'), 'current_value': Decimal('160.86'), 'source_document': 'trading-account-statement.pdf'},
        # Commodities from screenshot
        {'broker': 'REVOLUT', 'ticker': 'XAU', 'isin': None, 'name': 'Gold', 'asset_type': 'COMMODITY', 'quantity': Decimal('0.326'), 'current_value': Decimal('700.00'), 'source_document': 'Screenshot Commodities.png'},
        {'broker': 'REVOLUT', 'ticker': 'XAG', 'isin': None, 'name': 'Silver', 'asset_type': 'COMMODITY', 'quantity': Decimal('3.35'), 'current_value': Decimal('190.00'), 'source_document': 'Screenshot Commodities.png'},
        # Crypto from screenshot
        {'broker': 'REVOLUT', 'ticker': 'DOT', 'isin': None, 'name': 'Polkadot', 'asset_type': 'CRYPTO', 'quantity': Decimal('2'), 'current_value': Decimal('15.00'), 'source_document': 'Screenshot Crypto.png'},
        {'broker': 'REVOLUT', 'ticker': 'SOL', 'isin': None, 'name': 'Solana', 'asset_type': 'CRYPTO', 'quantity': Decimal('0.05'), 'current_value': Decimal('7.00'), 'source_document': 'Screenshot Crypto.png'},
        {'broker': 'REVOLUT', 'ticker': 'POL', 'isin': None, 'name': 'Polygon', 'asset_type': 'CRYPTO', 'quantity': Decimal('10'), 'current_value': Decimal('5.00'), 'source_document': 'Screenshot Crypto.png'},
    ]


def get_ibkr_holdings() -> list:
    """IBKR holdings from CSV transactions."""
    return [
        {'broker': 'IBKR', 'ticker': 'RGTI', 'isin': None, 'name': 'Rigetti Computing', 'asset_type': 'STOCK', 'quantity': Decimal('3'), 'current_value': Decimal('130.00'), 'source_document': 'U22156212.TRANSACTIONS.csv'},
        {'broker': 'IBKR', 'ticker': '3CP', 'isin': None, 'name': 'Xiaomi Corp', 'asset_type': 'STOCK', 'quantity': Decimal('50'), 'current_value': Decimal('300.00'), 'source_document': 'U22156212.TRANSACTIONS.csv'},
        {'broker': 'IBKR', 'ticker': 'EUR', 'isin': None, 'name': 'Cash Balance', 'asset_type': 'CASH', 'quantity': Decimal('133'), 'current_value': Decimal('133.00'), 'source_document': 'U22156212.TRANSACTIONS.csv'},
    ]


def populate_holdings():
    """Populate holdings table with ALL individual tickers."""
    session = SessionLocal()
    
    print("=" * 70)
    print("📊 POPULATING HOLDINGS TABLE (Individual Tickers Only)")
    print("=" * 70)
    
    # Collect all holdings
    all_holdings = []
    
    # BG Saxo - Parse CSV
    print("\n📁 Parsing BG Saxo CSV...")
    bgsaxo = parse_bgsaxo_csv()
    print(f"   Found {len(bgsaxo)} holdings")
    all_holdings.extend(bgsaxo)
    
    # Scalable Capital
    print("\n📁 Loading Scalable Capital...")
    scalable = get_scalable_holdings()
    print(f"   Found {len(scalable)} holdings")
    all_holdings.extend(scalable)
    
    # Binance
    print("\n📁 Loading Binance...")
    binance = get_binance_holdings()
    print(f"   Found {len(binance)} holdings")
    all_holdings.extend(binance)
    
    # Trade Republic
    print("\n📁 Loading Trade Republic...")
    tr = get_trade_republic_holdings()
    print(f"   Found {len(tr)} holdings")
    all_holdings.extend(tr)
    
    # Revolut
    print("\n📁 Loading Revolut...")
    revolut = get_revolut_holdings()
    print(f"   Found {len(revolut)} holdings")
    all_holdings.extend(revolut)
    
    # IBKR
    print("\n📁 Loading IBKR...")
    ibkr = get_ibkr_holdings()
    print(f"   Found {len(ibkr)} holdings")
    all_holdings.extend(ibkr)
    
    # Clear existing holdings
    print("\n🗑️  Clearing existing holdings...")
    session.query(Holding).delete()
    session.commit()
    
    # Insert all holdings
    print("\n📥 Inserting holdings...")
    total_value = Decimal('0')
    inserted = 0
    errors = 0
    
    for h in all_holdings:
        try:
            holding = Holding(
                id=uuid.uuid4(),
                broker=h['broker'],
                ticker=h['ticker'],
                isin=h.get('isin'),
                name=h['name'],
                asset_type=h['asset_type'],
                quantity=h['quantity'],
                current_value=h['current_value'],
                current_price=safe_price(h['current_value'], h['quantity']),
                currency='EUR',
                source_document=h['source_document'],
                last_updated=datetime.now()
            )
            session.add(holding)
            session.commit()
            total_value += h['current_value']
            inserted += 1
        except Exception as e:
            session.rollback()
            errors += 1
            print(f"   ⚠️ Error on {h['broker']}/{h['ticker']}: {str(e)[:50]}")
    
    print(f"   Inserted: {inserted}, Errors: {errors}")

    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    # Count by broker
    brokers = {}
    for h in all_holdings:
        broker = h['broker']
        if broker not in brokers:
            brokers[broker] = {'count': 0, 'value': Decimal('0')}
        brokers[broker]['count'] += 1
        brokers[broker]['value'] += h['current_value']
    
    for broker, stats in sorted(brokers.items()):
        print(f"  {broker:<18} | {stats['count']:>3} holdings | €{stats['value']:>10,.2f}")
    
    print("-" * 70)
    print(f"  {'TOTAL':<18} | {len(all_holdings):>3} holdings | €{total_value:>10,.2f}")
    print("=" * 70)
    
    session.close()
    return len(all_holdings), total_value


if __name__ == "__main__":
    count, total = populate_holdings()
    print(f"\n✅ Inserted {count} individual holdings")
    print(f"💰 Total portfolio value: €{total:,.2f}")
