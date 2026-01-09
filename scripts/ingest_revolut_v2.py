"""
REVOLUT Ingestion Script v2
Dedicated ingestion for Revolut Excel + PDF exports.

Input files:
- trading-account-statement PDF -> Holdings stocks (with ISIN)
- crypto-account-statement PDF -> Holdings crypto
- trading-account-statement Excel -> Transactions stocks
- crypto-account-statement Excel -> Transactions crypto
- account-statement Excel (2022) -> Transactions XAU/XAG
- account-statement Excel (2017) -> Transactions cash/transfers

Output:
- Populates holdings and transactions tables in PostgreSQL
"""
import pandas as pd
import pypdf
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
import uuid
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "REVOLUT"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\revolut")


def safe_decimal(value, default=Decimal("0")) -> Decimal:
    """Safely convert value to Decimal."""
    if pd.isna(value) or value is None:
        return default
    try:
        val_str = str(value).replace(",", ".").replace("$", "").replace("€", "").replace("%", "").strip()
        # Handle negative in parentheses: (123.45) -> -123.45
        if val_str.startswith("(") and val_str.endswith(")"):
            val_str = "-" + val_str[1:-1]
        return Decimal(val_str)
    except (InvalidOperation, ValueError):
        return default


def parse_date(value) -> datetime:
    """Parse various date formats from Revolut."""
    if pd.isna(value) or value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    val_str = str(value)
    # Try ISO format first
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %y"]:
        try:
            return datetime.strptime(val_str[:26], fmt)
        except ValueError:
            continue
    return datetime.now()


def read_revolut_excel(filepath: Path) -> pd.DataFrame:
    """Read Revolut Excel files (CSV-in-single-cell format)."""
    df_raw = pd.read_excel(filepath, engine='calamine', header=None)
    csv_text = '\n'.join(df_raw[0].astype(str).tolist())
    return pd.read_csv(StringIO(csv_text))


# ============================================================
# HOLDINGS EXTRACTION FROM PDFs
# ============================================================

def extract_holdings_from_trading_pdf(filepath: Path) -> list:
    """Extract stock holdings from trading-account-statement PDF."""
    print(f"\n📦 Extracting stock holdings from: {filepath.name}")
    
    holdings = []
    reader = pypdf.PdfReader(filepath)
    
    for page in reader.pages:
        text = page.extract_text()
        
        # Look for Portfolio breakdown section
        if "Portfolio breakdown" in text or "ISIN" in text:
            # Pattern: SYMBOL Company ISIN Quantity Price Value
            # Example: GOOGL Alphabet (Class A) US02079K3059 2 US$314.09 US$628.18
            lines = text.split('\n')
            for line in lines:
                # Match pattern with ISIN (12 char code starting with 2 letters)
                isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})\s+(\d+(?:\.\d+)?)\s+(?:US\$|€)?(\d+(?:\.\d+)?)', line)
                if isin_match:
                    isin = isin_match.group(1)
                    qty = isin_match.group(2)
                    price = isin_match.group(3)
                    
                    # Extract symbol (first word before company name)
                    symbol_match = re.match(r'^([A-Z]+)\s+', line)
                    symbol = symbol_match.group(1) if symbol_match else isin[:4]
                    
                    # Extract company name (between symbol and ISIN)
                    name_match = re.search(rf'^{symbol}\s+(.+?)\s+{isin}', line)
                    name = name_match.group(1).strip() if name_match else symbol
                    
                    holdings.append({
                        "ticker": symbol,
                        "isin": isin,
                        "name": name,
                        "quantity": safe_decimal(qty),
                        "price": safe_decimal(price),
                        "asset_type": "STOCK",
                        "currency": "USD"
                    })
    
    print(f"   Found {len(holdings)} stock holdings")
    return holdings


def extract_holdings_from_crypto_pdf(filepath: Path) -> list:
    """Extract crypto holdings from crypto-account-statement PDF."""
    print(f"\n📦 Extracting crypto holdings from: {filepath.name}")
    
    holdings = []
    reader = pypdf.PdfReader(filepath)
    
    # Only look at first page which has the summary
    text = reader.pages[0].extract_text()
    
    # Pattern: Symbol Asset Valore_iniziale ... Valore_finale
    # Example: POL POL (ex-MATIC) 0 POL ... 136,6432338 POL  12,69€
    lines = text.split('\n')
    
    # Find lines with crypto data (have format: SYMBOL Name ... Quantity SYMBOL  Value€)
    for i, line in enumerate(lines):
        # Match crypto symbols (uppercase, 2-5 chars)
        match = re.match(r'^([A-Z]{2,5})\s+(.+?)\s+(\d+(?:,\d+)?)\s+(?:[A-Z]+)', line)
        if match:
            symbol = match.group(1)
            name = match.group(2).strip()
            
            # Look for final value in same or next line
            qty_match = re.search(rf'(\d+(?:,\d+)?)\s+{symbol}\s+(\d+(?:,\d+)?)\s*€', line)
            if not qty_match and i + 1 < len(lines):
                qty_match = re.search(rf'(\d+(?:,\d+)?)\s*€', lines[i + 1])
            
            if qty_match:
                # Get quantity from "Valore finale" column
                final_qty_match = re.search(rf'(\d+(?:,\d+)?)\s+{symbol}', line.split("Valore finale")[-1] if "Valore finale" in line else line)
                if final_qty_match:
                    qty = final_qty_match.group(1).replace(",", ".")
                    value_eur = qty_match.group(1).replace(",", ".") if qty_match else "0"
                    
                    # Skip if quantity is 0
                    if float(qty) > 0:
                        holdings.append({
                            "ticker": symbol,
                            "isin": None,
                            "name": name,
                            "quantity": safe_decimal(qty),
                            "price": safe_decimal(value_eur) / safe_decimal(qty) if safe_decimal(qty) > 0 else Decimal("0"),
                            "asset_type": "CRYPTO",
                            "currency": "EUR"
                        })
    
    print(f"   Found {len(holdings)} crypto holdings")
    return holdings


# ============================================================
# TRANSACTIONS EXTRACTION FROM EXCEL
# ============================================================

def extract_transactions_from_trading_excel(filepath: Path) -> list:
    """Extract stock transactions from trading Excel."""
    print(f"\n📜 Extracting stock transactions from: {filepath.name}")
    
    df = read_revolut_excel(filepath)
    print(f"   Found {len(df)} rows")
    
    transactions = []
    for _, row in df.iterrows():
        ticker = str(row.get('Ticker', '')).strip()
        if not ticker or ticker == 'nan':
            continue
            
        tx_type = str(row.get('Type', '')).upper()
        operation = "BUY" if "BUY" in tx_type else "SELL" if "SELL" in tx_type else "OTHER"
        
        # Handle CASH TOP-UP and DIVIDEND
        if "DIVIDEND" in tx_type:
            operation = "DIVIDEND"
        elif "WITHDRAW" in tx_type:
             operation = "WITHDRAW"
        elif "TOP-UP" in tx_type:
             operation = "DEPOSIT"
        
        # Ensure total_amount is negative for BUY/WITHDRAW explicitly if not already
        # Revolut Excel usually has negative amounts for debits, but let's verify.
        # Check inspection: Column is 'Total Amount'.
        # Assuming signed values in Excel.
        
        transactions.append({
            "ticker": ticker,
            "isin": None,  # Not in Excel
            "operation": operation,
            "quantity": safe_decimal(row.get('Quantity', 0)),
            "price": safe_decimal(row.get('Price per share', 0)),
            "total_amount": safe_decimal(row.get('Total Amount', row.get('Amount', df.get('Value', 0)))), # Fallback to Amount or Value
            "balance": safe_decimal(row.get('Balance', 0)), # Capture Balance for cash calc
            "currency": str(row.get('Currency', 'USD')).strip()[:3],
            "timestamp": parse_date(row.get('Date')),
            "asset_type": "STOCK"
        })
    
    print(f"   Extracted {len(transactions)} stock transactions")
    return transactions


def extract_transactions_from_crypto_excel(filepath: Path) -> list:
    """Extract crypto transactions from crypto Excel."""
    print(f"\n📜 Extracting crypto transactions from: {filepath.name}")
    
    df = read_revolut_excel(filepath)
    print(f"   Found {len(df)} rows")
    
    transactions = []
    for _, row in df.iterrows():
        symbol = str(row.get('Symbol', '')).strip()
        if not symbol or symbol == 'nan':
            continue
            
        tx_type = str(row.get('Type', '')).lower()
        
        # Map Italian transaction types to standard operations
        if 'acquist' in tx_type or 'buy' in tx_type:
            operation = "BUY"
        elif 'vend' in tx_type or 'sell' in tx_type:
            operation = "SELL"
        elif 'staking' in tx_type or 'ricompensa' in tx_type:
            operation = "STAKING_REWARD"
        elif 'learn' in tx_type or 'earn' in tx_type:
            operation = "REWARD"
        elif 'invio' in tx_type or 'send' in tx_type:
            operation = "TRANSFER_OUT"
        elif 'ricezione' in tx_type or 'receive' in tx_type:
            operation = "TRANSFER_IN"
        elif 'exchange' in tx_type or 'cambio' in tx_type:
            operation = "EXCHANGE"
        else:
            operation = "OTHER"
        
        transactions.append({
            "ticker": symbol,
            "isin": None,
            "operation": operation,
            "quantity": safe_decimal(row.get('Quantity', 0)),
            "price": safe_decimal(row.get('Price', 0)),
            "total_amount": safe_decimal(row.get('Value', row.get('Amount', 0))),
            "currency": str(row.get('Currency', 'EUR')).strip()[:3] if pd.notna(row.get('Currency')) else 'EUR',
            "timestamp": parse_date(row.get('Date')),
            "asset_type": "CRYPTO"
        })
    
    print(f"   Extracted {len(transactions)} crypto transactions")
    return transactions



def extract_transactions_from_commodities_excel(filepath: Path) -> list:
    """Extract XAU/XAG transactions from commodities account Excel."""
    print(f"\n📜 Extracting commodities transactions from: {filepath.name}")
    
    df = read_revolut_excel(filepath)
    print(f"   Found {len(df)} rows")
    
    transactions = []
    for _, row in df.iterrows():
        currency = str(row.get('Valuta', '')).strip()
        # Only XAU and XAG are commodities
        if currency not in ['XAU', 'XAG']:
            continue
            
        tx_type = str(row.get('Tipo', '')).lower()
        operation = "BUY" if "acquist" in tx_type or "cambia" in tx_type else "SELL" if "vend" in tx_type else "OTHER"
        
        transactions.append({
            "ticker": currency,  # XAU or XAG
            "isin": None,
            "operation": operation,
            "quantity": abs(safe_decimal(row.get('Importo', 0))),
            "price": safe_decimal(row.get('Costo', 0)),
            "total_amount": safe_decimal(row.get('Saldo', 0)),
            "currency": currency,
            "timestamp": parse_date(row.get('Data di completamento', row.get('Data di inizio'))),
            "asset_type": "COMMODITY"
        })
    
    print(f"   Extracted {len(transactions)} commodities transactions")
    return transactions


# ============================================================
# DATABASE LOADING
# ============================================================

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
            source_document="Revolut PDF",
            last_updated=datetime.now()
        )
        session.add(holding)
        count += 1
    
    return count


def load_transactions(transactions: list, session) -> int:
    """Load transactions into database."""
    count = 0
    for tx in transactions:
        if tx["quantity"] == 0 and tx["total_amount"] == 0:
            continue
            
        transaction = Transaction(
            id=uuid.uuid4(),
            broker=BROKER,
            ticker=str(tx["ticker"])[:20],
            isin=tx.get("isin"),
            operation=tx["operation"],
            status="COMPLETED",
            quantity=abs(tx["quantity"]) if tx["quantity"] else Decimal("1"),
            price=tx["price"] if tx["price"] else abs(tx["total_amount"]),
            total_amount=tx["total_amount"],
            currency=tx.get("currency", "EUR")[:3],
            fees=Decimal("0"),
            timestamp=tx["timestamp"],
            source_document=tx.get("source", "Revolut Excel")
        )
        session.add(transaction)
        count += 1
    
    return count


def calculate_holdings_from_transactions(transactions: list, asset_types: list) -> list:
    """Calculate current holdings from transaction history."""
    from collections import defaultdict
    
    # Aggregate by ticker and asset_type
    positions = defaultdict(lambda: {"qty": Decimal("0"), "total_cost": Decimal("0"), "asset_type": None, "currency": "EUR"})
    
    for tx in transactions:
        if tx.get("asset_type") not in asset_types:
            continue
            
        ticker = tx["ticker"]
        qty = tx.get("quantity", Decimal("0"))
        price = tx.get("price", Decimal("0"))
        
        if tx["operation"] in ["BUY", "STAKING_REWARD", "REWARD", "TRANSFER_IN"]:
            positions[ticker]["qty"] += qty
            positions[ticker]["total_cost"] += qty * price
        elif tx["operation"] in ["SELL", "TRANSFER_OUT", "EXCHANGE"]:
            positions[ticker]["qty"] -= qty
            
        positions[ticker]["asset_type"] = tx.get("asset_type", "CRYPTO")
        positions[ticker]["currency"] = tx.get("currency", "EUR")
    
    holdings = []
    for ticker, data in positions.items():
        if data["qty"] > Decimal("0.00001"):  # Skip dust
            avg_price = data["total_cost"] / data["qty"] if data["qty"] > 0 else Decimal("0")
            holdings.append({
                "ticker": ticker,
                "isin": None,
                "name": ticker,
                "quantity": data["qty"],
                "price": avg_price,
                "asset_type": data["asset_type"],
                "currency": data["currency"]
            })
    
    return holdings



def calculate_usd_cash(transactions: list) -> dict:
    """Calculate USD Cash balance from latest Stock transaction."""
    stock_tx = [t for t in transactions if t.get("asset_type") == "STOCK" and t.get("balance") is not None]
    
    if not stock_tx:
        return None
        
    # Sort by timestamp ascending
    stock_tx.sort(key=lambda x: x["timestamp"])
    
    # Get last balance
    last_tx = stock_tx[-1]
    last_balance = last_tx["balance"]
    
    print(f"   💰 USD Cash (Trading) found: {last_balance} USD (from {last_tx['timestamp'].date()})")
    
    if last_balance > 0:
        return {
            "ticker": "USD",
            "isin": None,
            "name": "Revolut Trading Cash (USD)",
            "quantity": last_balance,
            "price": Decimal("1"), # It's cash
            "asset_type": "CASH",
            "currency": "USD"
        }
    return None

# ============================================================
# MAIN INGESTION
# ============================================================

def run_ingestion():
    """Main ingestion routine."""
    print("=" * 60)
    print("🚀 REVOLUT INGESTION v2")
    print("=" * 60)
    
    session = SessionLocal()
    
    try:
        # Clear existing Revolut data
        deleted_h = session.query(Holding).filter(Holding.broker == BROKER).delete()
        deleted_t = session.query(Transaction).filter(Transaction.broker == BROKER).delete()
        print(f"\n🗑️ Cleared {deleted_h} holdings, {deleted_t} transactions")
        
        all_holdings = []
        all_transactions = []
        
        # 1. Extract holdings from PDFs
        trading_pdfs = list(INBOX.glob("trading-account-statement*.pdf"))
        for pdf in trading_pdfs:
            all_holdings.extend(extract_holdings_from_trading_pdf(pdf))
        
        crypto_pdfs = list(INBOX.glob("crypto-account-statement*.pdf"))
        for pdf in crypto_pdfs:
            all_holdings.extend(extract_holdings_from_crypto_pdf(pdf))
        
        # 2. Extract transactions from Excel
        trading_excels = list(INBOX.glob("trading-account-statement*.xlsx"))
        for excel in trading_excels:
            all_transactions.extend(extract_transactions_from_trading_excel(excel))
        
        crypto_excels = list(INBOX.glob("crypto-account-statement*.xlsx"))
        for excel in crypto_excels:
            all_transactions.extend(extract_transactions_from_crypto_excel(excel))
        
        commodities_excels = list(INBOX.glob("account-statement_2022*.xlsx"))
        for excel in commodities_excels:
            all_transactions.extend(extract_transactions_from_commodities_excel(excel))
        
        # 3. Load transactions into database FIRST
        tx_count = load_transactions(all_transactions, session)
        
        # 4. Calculate holdings for crypto and commodities from transactions
        # (since PDF parsing is unreliable for these)
        print("\n📊 Calculating holdings from transaction history...")
        crypto_holdings = calculate_holdings_from_transactions(all_transactions, asset_types=["CRYPTO", "COMMODITY"])
        all_holdings.extend(crypto_holdings)
        print(f"   Calculated {len(crypto_holdings)} crypto/commodity holdings")
        
        # Calculate USD Cash
        usd_cash = calculate_usd_cash(all_transactions)
        if usd_cash:
            all_holdings.append(usd_cash)
        
        # 5. Load all holdings into database
        holdings_count = load_holdings(all_holdings, session)

        
        # 4. Log import
        log = ImportLog(
            id=uuid.uuid4(),
            broker=BROKER,
            filename="Revolut batch ingestion",
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
        
        # Invalidate cache
        cache_path = Path(__file__).parent.parent / "data" / "portfolio_snapshot.json"
        if cache_path.exists():
            cache_path.unlink()
            print("🔄 Portfolio cache invalidated (Dashboard will refresh)")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_ingestion()
