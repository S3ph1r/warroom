
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.price_service_v5 import isin_to_yahoo_ticker, clean_ticker, get_yahoo_price

test_cases = [
    # ISIN, Original Ticker, Expected Result (Approx)
    ("NL0010273215", "NL0010273215", "ASML.AS"), # ASML Amsterdam
    ("US74736K1016", "QRVO:xnas", "QRVO"),        # Qorvo (MIC cleanup)
    ("FR0010221234", "ETL:xpar", "ETL.PA"),       # Eutelsat (MIC + ISIN prefix)
    ("IE00B4L5Y983", "SWDA", "SWDA.MI"),          # iShares World (Manual/ISIN)
    ("DK0060534915", "NOVO NORDISK B A/S", "NOVO-B.CO"), # Novo (Junk cleanup + manual/prefix)
    ("US70450Y1038", "PYPL:xnas", "PYPL"),        # PayPal (MIC cleanup)
]

print("=== TICKER RESOLUTION TEST ===")
for isin, ticker, expected in test_cases:
    cleaned = clean_ticker(ticker)
    resolved = isin_to_yahoo_ticker(isin, cleaned)
    print(f"ISIN: {isin:15} | Orig: {ticker:20} | Cleaned: {cleaned:15} | Resolved: {resolved:12} | Expected: {expected}")

print("\n=== PRICE FETCH TEST (LIVE) ===")
# Testing a few live fetches
for isin, ticker, expected in test_cases[:3]:
    price, source, success, change = get_yahoo_price(ticker, isin)
    print(f"Ticker: {ticker:15} | Price: {price:8} | Source: {source:15} | Success: {success}")

