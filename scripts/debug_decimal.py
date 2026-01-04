from decimal import Decimal

def test_decimal(val):
    print(f"Original: {repr(val)}")
    try:
        d = Decimal(str(val))
        print(f"Converted: {d}")
    except Exception as e:
        print(f"CRASH: {e}")

# Scenarios likely to come from LLM (Italian PDF)
test_decimal(10.5)         # Valid float
test_decimal("10.5")       # Valid string
test_decimal("1.234,56")   # European format string -> CRASH expected
test_decimal("-1.170,68")  # Negative European -> CRASH expected
test_decimal("1,000")      # Comma as thousands? Or decimal? Python Decimal(str("1,000")) crashes.
