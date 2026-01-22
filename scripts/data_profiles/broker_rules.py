"""
Centralized configuration for Broker Data Normalization.
Defines format rules for numbers, dates, and other broker-specific quirks.
Used by smart_loader.py and smart_extractor.py.
"""

BROKER_RULES = {
    "BGSAXO": {
        "decimal_separator": ",",
        "thousand_separator": ".",
        "date_format": "%d-%b-%Y",  # Example: 19-dic-2025 (needs custom parsing for months usually)
        "description": "European number format (1.234,56)"
    },
    "SCALABLE": {
        "decimal_separator": ",",
        "thousand_separator": ".",
        "description": "German broker, typically EU format"
    },
    "REVOLUT": {
        "decimal_separator": ".", 
        "thousand_separator": ",",
        "description": "US/International format"
    },
    "IBKR": {
        "decimal_separator": ".",
        "thousand_separator": ",",
        "description": "US format"
    },
    "BINANCE": {
        "decimal_separator": ".",
        "thousand_separator": ",",
        "description": "Crypto standard (US format)"
    },
    # Fallback
    "DEFAULT": {
        "decimal_separator": ".",
        "thousand_separator": ",",
        "description": "Standard US format (1,234.56)"
    }
}

def get_broker_rule(broker_name: str) -> dict:
    """Retrieve rules for a broker, falling back to DEFAULT."""
    if not broker_name:
        return BROKER_RULES["DEFAULT"]
    
    # Normalize key (e.g. "BG SAXO" -> "BGSAXO")
    key = broker_name.upper().replace(" ", "").replace("_", "")
    
    # Direct match
    if key in BROKER_RULES:
        return BROKER_RULES[key]
    
    # Fuzzy match attempts
    for k in BROKER_RULES:
        if k in key or key in k:
            return BROKER_RULES[k]
            
    return BROKER_RULES["DEFAULT"]
