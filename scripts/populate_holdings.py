"""
Populate Holdings Table
Inserts validated portfolio data into the new holdings table.
"""
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding


def populate_holdings():
    """Populate holdings table with validated portfolio data."""
    session = SessionLocal()
    
    print("=" * 60)
    print("📊 POPULATING HOLDINGS TABLE")
    print("=" * 60)
    
    # Validated portfolio data (2025-12-20)
    holdings_data = [
        # BG SAXO - €18,502 (from CSV Posizioni)
        {"broker": "BG_SAXO", "ticker": "PORTFOLIO", "name": "BG Saxo Portfolio Aggregate", "asset_type": "STOCK", "quantity": Decimal("1"), "current_value": Decimal("18502.00"), "source_document": "Posizioni_19-dic-2025.csv"},
        
        # SCALABLE CAPITAL - €4,399.06 (from PDF Financial Status)
        {"broker": "SCALABLE_CAPITAL", "ticker": "TSLA", "name": "Tesla", "isin": "US88160R1014", "asset_type": "STOCK", "quantity": Decimal("1"), "current_value": Decimal("411.35"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "BIDU", "name": "Baidu A", "isin": "KYG070341048", "asset_type": "STOCK", "quantity": Decimal("17"), "current_value": Decimal("215.90"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "UBER", "name": "Uber Technologies", "isin": "US90353T1007", "asset_type": "STOCK", "quantity": Decimal("5"), "current_value": Decimal("339.80"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "BABA", "name": "Alibaba Group", "isin": "KYG017191142", "asset_type": "STOCK", "quantity": Decimal("20"), "current_value": Decimal("315.60"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "BYDDF", "name": "BYD Co. ADR", "isin": "US05606L1008", "asset_type": "STOCK", "quantity": Decimal("12"), "current_value": Decimal("124.80"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "QBTS", "name": "D-Wave Quantum", "isin": "US26740W1099", "asset_type": "STOCK", "quantity": Decimal("25"), "current_value": Decimal("528.75"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "XIACY", "name": "Xiaomi", "isin": "KYG9830T1067", "asset_type": "STOCK", "quantity": Decimal("120"), "current_value": Decimal("531.60"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "TCEHY", "name": "Tencent Holdings", "isin": "KYG875721634", "asset_type": "STOCK", "quantity": Decimal("10"), "current_value": Decimal("663.00"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "EL", "name": "EssilorLuxottica", "isin": "US2972842007", "asset_type": "STOCK", "quantity": Decimal("6"), "current_value": Decimal("828.00"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "MIDA", "name": "Midea Group Co", "isin": "CNE100006M58", "asset_type": "STOCK", "quantity": Decimal("20"), "current_value": Decimal("188.00"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "IXC", "name": "iShares S&P 500 Energy", "isin": "IE00B42NKQ00", "asset_type": "ETF", "quantity": Decimal("10"), "current_value": Decimal("77.80"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "HTWO", "name": "L&G Hydrogen Economy", "isin": "IE00BMYDM794", "asset_type": "ETF", "quantity": Decimal("17"), "current_value": Decimal("91.29"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "EWZ", "name": "iShares MSCI Brazil", "isin": "IE00B0M63516", "asset_type": "ETF", "quantity": Decimal("3"), "current_value": Decimal("65.61"), "source_document": "20251219 Financial status.pdf"},
        {"broker": "SCALABLE_CAPITAL", "ticker": "EUR", "name": "Cash Balance", "asset_type": "CASH", "quantity": Decimal("17.56"), "current_value": Decimal("17.56"), "source_document": "20251219 Financial status.pdf"},
        
        # BINANCE - €3,600 (from PDF Account Statement)
        {"broker": "BINANCE", "ticker": "CRYPTO_PORTFOLIO", "name": "Binance Crypto Portfolio", "asset_type": "CRYPTO", "quantity": Decimal("1"), "current_value": Decimal("3600.00"), "source_document": "AccountStatementPeriod.pdf"},
        
        # TRADE REPUBLIC - €2,826.07 (from Screenshot)
        {"broker": "TRADE_REPUBLIC", "ticker": "ASML", "name": "ASML Holding", "isin": "NL0010273215", "asset_type": "STOCK", "quantity": Decimal("2"), "current_value": Decimal("1801.80"), "source_document": "Screenshot 20-dic-2025.png"},
        {"broker": "TRADE_REPUBLIC", "ticker": "RACE", "name": "Ferrari", "isin": "NL0011585146", "asset_type": "STOCK", "quantity": Decimal("1"), "current_value": Decimal("322.90"), "source_document": "Screenshot 20-dic-2025.png"},
        {"broker": "TRADE_REPUBLIC", "ticker": "RBOT", "name": "iShares Automation & Robotics", "isin": "IE00BYZK4552", "asset_type": "ETF", "quantity": Decimal("20"), "current_value": Decimal("274.40"), "source_document": "Screenshot 20-dic-2025.png"},
        {"broker": "TRADE_REPUBLIC", "ticker": "HO", "name": "Thales", "isin": "FR0000121329", "asset_type": "STOCK", "quantity": Decimal("1"), "current_value": Decimal("228.40"), "source_document": "Screenshot 20-dic-2025.png"},
        {"broker": "TRADE_REPUBLIC", "ticker": "AFX", "name": "Carl Zeiss Meditec", "isin": "DE0005313704", "asset_type": "STOCK", "quantity": Decimal("3"), "current_value": Decimal("118.98"), "source_document": "Screenshot 20-dic-2025.png"},
        {"broker": "TRADE_REPUBLIC", "ticker": "9988", "name": "Alibaba Group", "isin": "KYG017191142", "asset_type": "STOCK", "quantity": Decimal("5"), "current_value": Decimal("79.59"), "source_document": "Screenshot 20-dic-2025.png"},
        
        # REVOLUT - €1,967 (from PDF + Screenshot)
        {"broker": "REVOLUT", "ticker": "GOOGL", "name": "Alphabet Class A", "isin": "US02079K3059", "asset_type": "STOCK", "quantity": Decimal("2"), "current_value": Decimal("553.76"), "currency": "USD", "source_document": "trading-account-statement.pdf"},
        {"broker": "REVOLUT", "ticker": "BIDU", "name": "Baidu", "isin": "US0567521085", "asset_type": "STOCK", "quantity": Decimal("3"), "current_value": Decimal("337.32"), "currency": "USD", "source_document": "trading-account-statement.pdf"},
        {"broker": "REVOLUT", "ticker": "BP", "name": "BP", "isin": "US0556221044", "asset_type": "STOCK", "quantity": Decimal("5"), "current_value": Decimal("160.86"), "currency": "USD", "source_document": "trading-account-statement.pdf"},
        {"broker": "REVOLUT", "ticker": "XAU", "name": "Gold", "asset_type": "COMMODITY", "quantity": Decimal("0.326"), "current_value": Decimal("700.00"), "source_document": "Screenshot Commodities.png"},
        {"broker": "REVOLUT", "ticker": "XAG", "name": "Silver", "asset_type": "COMMODITY", "quantity": Decimal("3.35"), "current_value": Decimal("190.00"), "source_document": "Screenshot Commodities.png"},
        {"broker": "REVOLUT", "ticker": "CRYPTO_BASKET", "name": "Crypto (DOT/SOL/POL)", "asset_type": "CRYPTO", "quantity": Decimal("1"), "current_value": Decimal("27.00"), "source_document": "Screenshot Crypto.png"},
        
        # IBKR - €500 (from user input)
        {"broker": "IBKR", "ticker": "EUR", "name": "Cash Deposit", "asset_type": "CASH", "quantity": Decimal("500"), "current_value": Decimal("500.00"), "source_document": "User Input"},
    ]
    
    # Clear existing holdings
    session.query(Holding).delete()
    session.commit()
    
    total_value = Decimal("0")
    
    for h in holdings_data:
        holding = Holding(
            id=uuid.uuid4(),
            broker=h["broker"],
            ticker=h["ticker"],
            isin=h.get("isin"),
            name=h["name"],
            asset_type=h["asset_type"],
            quantity=h["quantity"],
            current_value=h["current_value"],
            current_price=h["current_value"] / h["quantity"] if h["quantity"] > 0 else Decimal("0"),
            currency=h.get("currency", "EUR"),
            source_document=h["source_document"],
            last_updated=datetime.now()
        )
        session.add(holding)
        total_value += h["current_value"]
        print(f"  {h['broker']:<18} | {h['ticker']:<20} | €{h['current_value']:>10,.2f}")
    
    session.commit()
    print("-" * 60)
    print(f"  {'TOTAL':<18} | {'':<20} | €{total_value:>10,.2f}")
    print("=" * 60)
    print(f"✅ Inserted {len(holdings_data)} holdings")
    session.close()


if __name__ == "__main__":
    populate_holdings()
