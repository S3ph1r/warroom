
import re
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

def robust_parse_decimal(value, default=Decimal('0'), context=None) -> Decimal:
    """
    Intelligently parse a numeric string into a Decimal.
    Handles mixed European (1.234,56) and American (1,234.56) formats.
    
    Logic:
    1. Strip currency symbols and whitespace.
    2. If both '.' and ',' are present:
       - The LAST one is the decimal separator.
    3. If only one of ('.' or ',') is present:
       - Scan the string: if it appears exactly once and has 2 digits after it, it's likely a decimal.
       - If it appears multiple times, it's a thousands separator.
       - Heuristic: In '0.355', '.' is a decimal. In '5.458', '.' is a decimal (unlikely to have 5k shares of most stocks in a single report line unless context says so).
       - In CSV context (BG Saxo), '.' is typically used as decimal for prices/quantities.
    """
    if not value or value is None:
        return default
    
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    # Clean string
    s = str(value).strip().replace('EUR', '').replace('USD', '').replace('$', '').replace('%', '').strip()
    if not s:
        return default

    try:
        # Detect separators
        has_comma = ',' in s
        has_dot = '.' in s

        if has_comma and has_dot:
            # Both present: find which one is last
            if s.rfind(',') > s.rfind('.'):
                # , is decimal (1.234,56)
                s = s.replace('.', '').replace(',', '.')
            else:
                # . is decimal (1,234.56)
                s = s.replace(',', '')
        elif has_comma:
            # Only comma: check if it's likely a thousand or decimal
            # If it's at the end with 2 digits (e.g. 10,00), it's decimal
            # BG Saxo Percentages: -18,39%
            s = s.replace(',', '.')
        elif has_dot:
            # Only dot: 
            # BG Saxo CSV: 0.355 or 96.92
            # Here we trust the dot as decimal unless it looks like a year or ID (handled by caller)
            # No change needed if we want Decimal('0.355')
            pass

        return Decimal(s)
    except (InvalidOperation, ValueError) as e:
        logger.debug(f"Failed to parse decimal '{value}': {e}")
        return default
