import sys
from pathlib import Path
from decimal import Decimal

# Add root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from services.forex_service import get_exchange_rate, get_rates_for_currencies
except ImportError:
    print("❌ Could not import forex_service")
    sys.exit(1)

def test_forex():
    print("🌍 Testing Forex Service...")
    
    # Test DKK specifically
    print("\n--- TEST: DKK -> EUR ---")
    rate = get_exchange_rate('DKK', 'EUR')
    print(f"DKK -> EUR Rate: {rate}")
    
    if rate == 1.0 or rate == 1:
        print("⚠️ WARNING: Rate is 1.0, likely fallback!")
    else:
        print("✅ Rate looks valid.")

    # Test Batch
    print("\n--- TEST: Batch Fetch ['USD', 'DKK', 'HKD'] ---")
    rates = get_rates_for_currencies(['USD', 'DKK', 'HKD'])
    for curr, r in rates.items():
        print(f"{curr}: {r}")

if __name__ == "__main__":
    test_forex()
