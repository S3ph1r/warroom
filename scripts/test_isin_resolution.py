"""
Test the enhanced ISIN-to-ticker resolution.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from services.price_service_v5 import isin_to_yahoo_ticker, get_ticker_from_isin

# Test cases: (ISIN, raw_ticker, expected_result_pattern)
TEST_CASES = [
    # US Stocks with ISINs
    ("US83406F1021", "RIVIAN AUTOMOT.A", "RIVN"),  # Rivian
    ("FR0000121667", "ESSILORLUXOTTICA 1/2", "EL"),  # EssilorLuxottica (Paris)
    ("US90353T1007", "UBER TECH. DL-", "UBER"),  # Uber
    ("US67066G1040", "NVIDIA Corp.", "NVDA"),  # NVIDIA
    ("IT0004056880", "Amplifon", "AMP"),  # Amplifon (Milan)
    ("US0231351067", "AMZN", "AMZN"),  # Amazon
]

def test():
    print("--- TESTING ISIN RESOLUTION ---\n")
    
    for isin, raw, expected in TEST_CASES:
        # First test OpenFIGI directly
        figi = get_ticker_from_isin(isin)
        figi_ticker = figi['ticker'] if figi else "N/A"
        figi_exch = figi['exchange'] if figi else "N/A"
        
        # Then test full resolution
        resolved = isin_to_yahoo_ticker(isin, raw)
        
        match = "✅" if expected.lower() in resolved.lower() else "❌"
        print(f"{match} ISIN={isin[:6]}... | Raw='{raw[:20]:<20}' | FIGI={figi_ticker}({figi_exch}) | Resolved={resolved}")

if __name__ == "__main__":
    test()
