"""
TRADE REPUBLIC Ingestion Script v2
Dedicated ingestion for Trade Republic PDF exports.

Input files:
- Estratto conto.pdf -> All transactions (trades, dividends, interest, transfers)

Output:
- Populates holdings (calculated from transactions) and transactions tables in PostgreSQL
"""
import pypdf
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import uuid
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "TRADEREPUBLIC"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\traderepublic")

# Italian month mapping
MONTH_MAP = {
    'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6,
    'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12
}


def safe_decimal(value, default=Decimal("0")) -> Decimal:
    """Safely convert value to Decimal."""
    if value is None:
        return default
    try:
        val_str = str(value).replace(",", ".").replace("€", "").replace(" ", "").strip()
        return Decimal(val_str)
    except (InvalidOperation, ValueError):
        return default


def parse_italian_date(date_str: str, year_hint: int = 2025) -> datetime:
    """Parse Italian date format like '19 set 2024' or '19 set'."""
    try:
        parts = date_str.strip().split()
        day = int(parts[0])
        month = MONTH_MAP.get(parts[1].lower(), 1)
        year = int(parts[2]) if len(parts) > 2 else year_hint
        return datetime(year, month, day)
    except (ValueError, IndexError, KeyError):
        return datetime.now()


def extract_transactions_from_pdf(filepath: Path) -> list:
    """Extract all transactions from Trade Republic PDF."""
    print(f"\n📜 Extracting transactions from: {filepath.name}")
    
    transactions = []
    reader = pypdf.PdfReader(filepath)
    
    current_year = 2025  # Default year
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip header and footer lines
            if any(skip in line for skip in ['TRADE REPUBLIC', 'Trade Republic', 'Generato il', 'Pagina', 'DATA TIPO', 'www.traderepublic', 'P. IVA']):
                i += 1
                continue
            
            # Look for date pattern at start of line: "19 set" or "19 set 2024"
            date_match = re.match(r'^(\d{1,2}\s+\w{3}(?:\s+\d{4})?)', line)
            if date_match:
                date_str = date_match.group(1)
                
                # Check if year is in the date
                if re.search(r'\d{4}', date_str):
                    current_year = int(re.search(r'(\d{4})', date_str).group(1))
                
                # Get the rest of the line after date
                rest = line[len(date_str):].strip()
                
                # Sometimes the line continues on next line
                if i + 1 < len(lines) and not re.match(r'^\d{1,2}\s+\w{3}', lines[i + 1].strip()):
                    next_line = lines[i + 1].strip()
                    if not any(skip in next_line for skip in ['TRADE REPUBLIC', 'Trade Republic', 'Generato']):
                        rest = rest + " " + next_line
                        i += 1
                
                tx = parse_transaction_line(date_str, rest, current_year)
                if tx:
                    transactions.append(tx)
            
            i += 1
    
    print(f"   Extracted {len(transactions)} transactions")
    return transactions


def parse_transaction_line(date_str: str, line: str, year_hint: int) -> dict:
    """Parse a single transaction line."""
    
    timestamp = parse_italian_date(date_str, year_hint)
    
    # === BUY TRADE ===
    buy_match = re.search(r'Buy trade\s+([A-Z0-9]{12})\s+(.+?),\s*quantity:\s*(\d+)', line, re.IGNORECASE)
    if buy_match:
        isin = buy_match.group(1)
        name = buy_match.group(2).strip()
        qty = int(buy_match.group(3))
        
        # Extract amount
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": isin[:12],  # Use ISIN as ticker for now
            "isin": isin,
            "name": name,
            "operation": "BUY",
            "quantity": Decimal(str(qty)),
            "price": amount / Decimal(str(qty)) if qty > 0 else Decimal("0"),
            "total_amount": -amount,  # Negative for buy (money out)
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "ETF" if "ETF" in name.upper() or "UCITS" in name.upper() else "STOCK"
        }
    
    # === SELL TRADE ===
    sell_match = re.search(r'Sell trade\s+([A-Z0-9]{12})\s+(.+?),\s*quantity:\s*(\d+)', line, re.IGNORECASE)
    if sell_match:
        isin = sell_match.group(1)
        name = sell_match.group(2).strip()
        qty = int(sell_match.group(3))
        
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": isin[:12],
            "isin": isin,
            "name": name,
            "operation": "SELL",
            "quantity": Decimal(str(qty)),
            "price": amount / Decimal(str(qty)) if qty > 0 else Decimal("0"),
            "total_amount": amount,  # Positive for sell (money in)
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "ETF" if "ETF" in name.upper() or "UCITS" in name.upper() else "STOCK"
        }
    
    # === DIVIDEND ===
    div_match = re.search(r'(?:Cash )?Dividend for ISIN\s+([A-Z0-9]{12})', line, re.IGNORECASE)
    if div_match:
        isin = div_match.group(1)
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": isin[:12],
            "isin": isin,
            "name": f"Dividend {isin}",
            "operation": "DIVIDEND",
            "quantity": Decimal("1"),
            "price": amount,
            "total_amount": amount,
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "STOCK"
        }
    
    # === INTEREST ===
    if 'interest' in line.lower() or 'interess' in line.lower():
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": "CASH",
            "isin": None,
            "name": "Interest Payment",
            "operation": "INTEREST",
            "quantity": Decimal("1"),
            "price": amount,
            "total_amount": amount,
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "CASH"
        }
    
    # === DEPOSIT (Bonifico in) ===
    if 'bonifico' in line.lower() and ('deposito' in line.lower() or 'top up' in line.lower() or 'google pay' in line.lower()):
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": "CASH",
            "isin": None,
            "name": "Deposit",
            "operation": "DEPOSIT",
            "quantity": Decimal("1"),
            "price": amount,
            "total_amount": amount,
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "CASH"
        }
    
    # === WITHDRAW (Outgoing transfer) ===
    if 'outgoing transfer' in line.lower() or 'bonifico' in line.lower() and 'uscita' in line.lower():
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": "CASH",
            "isin": None,
            "name": "Withdrawal",
            "operation": "WITHDRAW",
            "quantity": Decimal("1"),
            "price": amount,
            "total_amount": -amount,
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "CASH"
        }
    
    # === TAX ===
    if 'tax' in line.lower() or 'impost' in line.lower():
        amount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', line)
        amount = safe_decimal(amount_match.group(1)) if amount_match else Decimal("0")
        
        return {
            "ticker": "TAX",
            "isin": None,
            "name": "Tax",
            "operation": "TAX",
            "quantity": Decimal("1"),
            "price": amount,
            "total_amount": -amount,
            "currency": "EUR",
            "timestamp": timestamp,
            "asset_type": "CASH"
        }
    
    return None


def calculate_holdings_from_transactions(transactions: list) -> list:
    """Calculate current holdings from transaction history."""
    positions = defaultdict(lambda: {
        "qty": Decimal("0"), 
        "total_cost": Decimal("0"), 
        "name": "", 
        "isin": None,
        "asset_type": "STOCK"
    })
    
    for tx in transactions:
        if tx["operation"] not in ["BUY", "SELL"]:
            continue
            
        isin = tx.get("isin")
        if not isin:
            continue
            
        if tx["operation"] == "BUY":
            positions[isin]["qty"] += tx["quantity"]
            positions[isin]["total_cost"] += tx["quantity"] * tx["price"]
        elif tx["operation"] == "SELL":
            positions[isin]["qty"] -= tx["quantity"]
            
        positions[isin]["name"] = tx.get("name", isin)
        positions[isin]["isin"] = isin
        positions[isin]["asset_type"] = tx.get("asset_type", "STOCK")
    
    holdings = []
    for isin, data in positions.items():
        if data["qty"] > 0:
            avg_price = data["total_cost"] / data["qty"] if data["qty"] > 0 else Decimal("0")
            holdings.append({
                "ticker": isin[:12],
                "isin": isin,
                "name": data["name"],
                "quantity": data["qty"],
                "price": avg_price,
                "asset_type": data["asset_type"],
                "currency": "EUR"
            })
    
    return holdings


def load_holdings(holdings: list, session) -> int:
    """Load holdings into database."""
    count = 0
    for h in holdings:
        if h["quantity"] <= 0:
            continue
            
        holding = Holding(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker=str(h["ticker"])[:20],
            isin=str(h["isin"])[:12] if h["isin"] else None,
            name=str(h["name"])[:255],
            asset_type=h["asset_type"],
            quantity=h["quantity"],
            purchase_price=h.get("price", Decimal("0")),
            current_price=h.get("price", Decimal("0")),
            current_value=h["quantity"] * h.get("price", Decimal("0")),
            currency=h.get("currency", "EUR")[:3],
            source_document="Trade Republic PDF",
            last_updated=datetime.now()
        )
        session.add(holding)
        count += 1
    
    return count


def load_transactions(transactions: list, session) -> int:
    """Load transactions into database."""
    count = 0
    for tx in transactions:
        transaction = Transaction(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker=str(tx["ticker"])[:20],
            isin=tx.get("isin"),
            operation=tx["operation"],
            status="COMPLETED",
            quantity=abs(tx["quantity"]),
            price=tx["price"],
            total_amount=tx["total_amount"],
            currency=tx.get("currency", "EUR")[:3],
            fees=Decimal("0"),
            timestamp=tx["timestamp"],
            source_document="Trade Republic PDF"
        )
        session.add(transaction)
        count += 1
    
    return count


def run_ingestion():
    """Main ingestion routine."""
    print("=" * 60)
    print("🚀 TRADE REPUBLIC INGESTION v2")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # Clear existing Trade Republic data
        deleted_h = session.query(Holding).filter(Holding.broker == BROKER).delete()
        deleted_t = session.query(Transaction).filter(Transaction.broker == BROKER).delete()
        print(f"\n🗑️ Cleared {deleted_h} holdings, {deleted_t} transactions")
        
        # Find PDF files
        pdf_files = list(INBOX.glob("*.pdf"))
        print(f"\n📂 Found {len(pdf_files)} PDF files")
        
        all_transactions = []
        
        # Extract transactions from PDFs
        for pdf in pdf_files:
            all_transactions.extend(extract_transactions_from_pdf(pdf))
        
        # Load transactions
        tx_count = load_transactions(all_transactions, session)
        
        # Calculate and load holdings
        print("\n📊 Calculating holdings from transactions...")
        holdings = calculate_holdings_from_transactions(all_transactions)
        print(f"   Calculated {len(holdings)} holdings")
        holdings_count = load_holdings(holdings, session)
        
        # Log import
        log = ImportLog(
            id=uuid.uuid4(),
            broker=BROKER,
            filename="Trade Republic batch ingestion",
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
