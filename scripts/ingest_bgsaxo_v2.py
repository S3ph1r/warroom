"""
BGSAXO Ingestion Script v2
Dedicated ingestion for BG SAXO Excel exports.

Input files:
- Posizioni_*.xlsx -> Holdings snapshot
- Transactions_*.xlsx -> All transactions (trades, dividends, deposits, etc.)

Output:
- Populates holdings and transactions tables in PostgreSQL
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
import uuid
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "BGSAXO"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\bgsaxo")


def safe_decimal(value, default=Decimal("0")) -> Decimal:
    """Safely convert value to Decimal."""
    if pd.isna(value):
        return default
    try:
        # Handle European format (comma as decimal separator)
        if isinstance(value, str):
            value = value.replace(",", ".").replace("%", "").strip()
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def parse_date(value) -> datetime:
    """Parse various date formats from BGSAXO."""
    if pd.isna(value):
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    # Try parsing string formats
    for fmt in ["%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return datetime.now()


    return datetime.now()


def parse_ticker_and_market(raw_input: str) -> tuple:
    """
    Split ticker format like 'INTC:xnas' into ('INTC', 'xnas').
    Returns (clean_ticker, market_code).
    """
    if not raw_input:
        return None, None
        
    s = str(raw_input).strip()
    if ':' in s:
        parts = s.split(':')
        return parts[0].strip(), parts[1].strip()
    
    return s, None


def map_operation_type(tipo_operazione: str, tipo: str) -> str:
    """Map BGSAXO operation types to our standard types."""
    tipo_lower = str(tipo_operazione).lower() if tipo_operazione else ""
    tipo_desc = str(tipo).lower() if tipo else ""
    
    if "contrattazione" in tipo_lower:
        if "vendi" in tipo_desc or "-" in tipo_desc:
            return "SELL"
        else:
            return "BUY"
    elif "capitale" in tipo_lower:
        if "dividend" in tipo_desc:
            return "DIVIDEND"
        return "CORPORATE_ACTION"
    elif "trasferimento" in tipo_lower or "liquidità" in tipo_lower:
        if "deposit" in tipo_desc.lower() or "deposito" in tipo_desc.lower():
            return "DEPOSIT"
        elif "preliev" in tipo_desc.lower() or "withdraw" in tipo_desc.lower():
            return "WITHDRAW"
        return "TRANSFER"
    elif "contanti" in tipo_lower:
        return "CASH"
    else:
        return "OTHER"


def ingest_holdings(filepath: Path, session) -> int:
    """Ingest holdings from Posizioni Excel file."""
    print(f"\n📦 Loading holdings from: {filepath.name}")
    
    df = pd.read_excel(filepath, engine='calamine')
    print(f"   Found {len(df)} rows")
    
    # Clear existing BGSAXO holdings
    deleted = session.query(Holding).filter(Holding.broker == BROKER).delete()
    print(f"   Deleted {deleted} existing BGSAXO holdings")
    
    count = 0
    for _, row in df.iterrows():
        # Skip empty rows
        if pd.isna(strumento) or not str(strumento).strip():
            continue
            
        raw_ticker = str(row.get('Ticker', '')).strip() if pd.notna(row.get('Ticker')) else strumento
        clean_ticker, market_code = parse_ticker_and_market(raw_ticker)
            
        holding = Holding(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker=clean_ticker[:20],  # Use clean ticker
            isin=str(row.get('ISIN', '')).strip()[:12] if pd.notna(row.get('ISIN')) else None,
            market=market_code[:10] if market_code else None,  # Store market
            name=str(strumento).strip()[:255],
            asset_type=_map_asset_type(row.get('Tipo attività', '')),
            quantity=safe_decimal(row.get('Quantità', 0)),
            purchase_price=safe_decimal(row.get('Prezzo di apertura')),
            purchase_date=parse_date(row.get('Data/ora apertura')).date() if pd.notna(row.get('Data/ora apertura')) else None,
            current_price=safe_decimal(row.get('Prz. corrente')),
            current_value=safe_decimal(row.get('Valore di mercato (EUR)', 0)),
            currency=str(row.get('Valuta', 'EUR')).strip()[:3] if pd.notna(row.get('Valuta')) else 'EUR',
            source_document=filepath.name,
            last_updated=datetime.now()
        )
        session.add(holding)
        count += 1
        
    session.commit()
    print(f"   ✅ Inserted {count} holdings")
    return count


def _map_asset_type(tipo: str) -> str:
    """Map BGSAXO asset type to our standard types."""
    if pd.isna(tipo):
        return "STOCK"
    tipo_lower = str(tipo).lower()
    if "etf" in tipo_lower:
        return "ETF"
    elif "azione" in tipo_lower or "stock" in tipo_lower:
        return "STOCK"
    elif "obblig" in tipo_lower or "bond" in tipo_lower:
        return "BOND"
    elif "crypto" in tipo_lower:
        return "CRYPTO"
    else:
        return "STOCK"


def ingest_transactions(filepath: Path, session) -> int:
    """Ingest transactions from Transactions Excel file."""
    print(f"\n📜 Loading transactions from: {filepath.name}")
    
    df = pd.read_excel(filepath, engine='calamine')
    print(f"   Found {len(df)} rows")
    
    # Delete existing BGSAXO transactions
    deleted = session.query(Transaction).filter(Transaction.broker == BROKER).delete()
    print(f"   Deleted {deleted} existing BGSAXO transactions")
    
    count = 0
    for _, row in df.iterrows():
        tipo_op = row.get('Tipo di operazione', '')
        tipo = row.get('Tipo', '')
        
        # Determine operation type
        operation = map_operation_type(tipo_op, tipo)
        
        # Get ticker/symbol
        strumento = row.get('Strumento', '')
        simbolo = row.get('Simbolo strumento', '')
        raw_ticker = str(simbolo).strip() if pd.notna(simbolo) and simbolo else (str(strumento) if strumento else "CASH")
        
        clean_ticker, market_code = parse_ticker_and_market(raw_ticker)
        
        # Parse quantity from Tipo field (e.g., "Vendi -4 @ 181.04 USD")
        quantity = Decimal("0")
        price = Decimal("0")
        tipo_str = str(tipo) if pd.notna(tipo) else ""
        
        if "@" in tipo_str:
            # Parse "Acquista 2 @ 301.93 USD" or "Vendi -4 @ 181.04 USD" format
            parts = tipo_str.split("@")
            try:
                qty_part = parts[0]
                # Remove all Italian verb variations
                for verb in ["Vendi", "Acquista", "Acquisto", "Compra", "Compro"]:
                    qty_part = qty_part.replace(verb, "")
                qty_part = qty_part.strip()
                quantity = safe_decimal(qty_part)
                price_part = parts[1].strip().split()[0]
                price = safe_decimal(price_part)
            except (IndexError, ValueError):
                pass

        
        # Get amounts
        importo = safe_decimal(row.get('Importo contabilizzato', 0))
        
        transaction = Transaction(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker=clean_ticker[:20],
            isin=str(row.get('Instrument ISIN', '')).strip()[:12] if pd.notna(row.get('Instrument ISIN')) else None,
            market=market_code[:10] if market_code else None,  # Store market
            operation=operation,
            status="COMPLETED",
            quantity=abs(quantity) if quantity else Decimal("1"),
            price=price if price else abs(importo),
            total_amount=importo,
            currency=str(row.get('Valuta', 'EUR')).strip()[:3] if pd.notna(row.get('Valuta')) else 'EUR',
            fees=safe_decimal(row.get('Costo totale', 0)),
            realized_pnl=safe_decimal(row.get('Profitti/perdite realizzati')) if pd.notna(row.get('Profitti/perdite realizzati')) else None,
            fx_cost=safe_decimal(row.get('Costo di conversione')) if pd.notna(row.get('Costo di conversione')) else None,
            timestamp=parse_date(row.get('Data della negoziazione')),
            source_document=filepath.name,
            notes=str(row.get('Commento', ''))[:500] if pd.notna(row.get('Commento')) else None
        )
        session.add(transaction)
        count += 1
        
    session.commit()
    print(f"   ✅ Inserted {count} transactions")
    return count


def run_ingestion():
    """Main ingestion routine."""
    print("=" * 60)
    print("🚀 BGSAXO INGESTION v2")
    print("=" * 60)
    
    # Find files
    posizioni_files = list(INBOX.glob("Posizioni_*.xlsx"))
    transactions_files = list(INBOX.glob("Transactions_*.xlsx"))
    
    print(f"\n📂 Found files in {INBOX}:")
    print(f"   Posizioni: {len(posizioni_files)} files")
    print(f"   Transactions: {len(transactions_files)} files")
    
    if not posizioni_files and not transactions_files:
        print("❌ No files found!")
        return
    
    session = SessionLocal()
    
    try:
        holdings_count = 0
        tx_count = 0
        
        # Process Posizioni (most recent)
        if posizioni_files:
            latest_pos = max(posizioni_files, key=lambda p: p.stat().st_mtime)
            holdings_count = ingest_holdings(latest_pos, session)
        
        # Process Transactions (most recent)
        if transactions_files:
            latest_tx = max(transactions_files, key=lambda p: p.stat().st_mtime)
            tx_count = ingest_transactions(latest_tx, session)
        
        # Log import
        log = ImportLog(
            id=uuid.uuid4(),
            broker=BROKER,
            filename=f"BGSAXO batch ingestion",
            holdings_created=holdings_count,
            transactions_created=tx_count,
            status="SUCCESS"
        )
        session.add(log)
        session.commit()
        
        print("\n" + "=" * 60)
        print("✅ INGESTION COMPLETE")
        print(f"   Holdings: {holdings_count}")
        print(f"   Transactions: {tx_count}")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_ingestion()
