"""
WAR ROOM - Forex Service
Handles dynamic exchange rate fetching and caching.
Replaces static FX rates in Price Service.
"""
import logging
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache file path
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "forex_cache.json")
CACHE_TTL = timedelta(hours=4) # Rates don't change that fast for our purpose, 4h is fine

# Standard Yahoo Finance Pairs (EUR base)
# Ticker format: "EUR{CUR}=X" -> Represents 1 EUR in CUR
# To get Rate (1 CUR in EUR), we do 1 / Price
SUPPORTED_CURRENCIES = ["USD", "GBP", "CHF", "CAD", "AUD", "JPY", "HKD", "CNY", "SEK", "DKK", "NOK"]

# Static fallback rates (approximate, just in case API fails completely)
FALLBACK_RATES = {
    'EUR': Decimal('1.0'),
    'USD': Decimal('0.95'),
    'GBP': Decimal('1.18'),
    'CHF': Decimal('1.06'),
    'CAD': Decimal('0.68'),
    'AUD': Decimal('0.63'),
    'JPY': Decimal('0.0065'),
    'HKD': Decimal('0.12'),
    'CNY': Decimal('0.13'),
    'SEK': Decimal('0.088'),
    'DKK': Decimal('0.134'),
    'NOK': Decimal('0.085'),
    'GBp': Decimal('0.0118'), # Pence
}

_forex_cache = {}

def load_cache():
    """Load cache from disk."""
    global _forex_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Convert back to types
                for k, v in data.items():
                    # v = [rate_float, timestamp_iso]
                    _forex_cache[k] = (Decimal(str(v[0])), datetime.fromisoformat(v[1]))
        except Exception as e:
            logger.warning(f"[FOREX] Failed to load cache: {e}")

def save_cache():
    """Save cache to disk."""
    try:
        data = {}
        for k, v in _forex_cache.items():
            rate, ts = v
            data[k] = (float(rate), ts.isoformat())
        
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"[FOREX] Failed to save cache: {e}")

# Initialize
load_cache()

def get_exchange_rate(from_currency: str, to_currency: str = "EUR") -> Decimal:
    """
    Get exchange rate to convert from_currency -> to_currency.
    Example: get_exchange_rate("USD", "EUR") returns ~0.95 (Value in EUR of 1 USD).
    """
    # Detect Pence Sterling (GBp) before normalization
    is_pence = False
    if from_currency == "GBp":
        is_pence = True

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    # 1. Identity
    if from_currency == to_currency and not is_pence:
        return Decimal('1.0')
        
    # 2. Handle Pence Sterling (GBp)
    if is_pence:
        # Get rate for full GBP and divide by 100
        # Recursive call but safe because now from_currency is GBP (upper)
        # But we must be careful: if we call get_exchange_rate("GBP", to_currency),
        # validation at top won't trigger is_pence.
        rate_gbp = get_exchange_rate("GBP", to_currency)
        return rate_gbp / Decimal('100')

    # 3. Check Cache
    cache_key = f"{from_currency}/{to_currency}"
    if cache_key in _forex_cache:
        rate, ts = _forex_cache[cache_key]
        if datetime.now() - ts < CACHE_TTL:
            return rate
        else:
            # Expired
            pass
    else:
        # Miss
        pass
    
    # 4. Fetch from Yahoo Finance
    # Standard pairs are EUR{CUR}=X.
    # Ex: EURUSD=X price is ~1.05 (1 EUR = 1.05 USD)
    
    pair = None
    inverse = False
    
    if from_currency == "EUR":
        # Converting EUR -> Foreign (e.g. for Frontend Toggle)
        # Pair: EUR{to_currency}=X
        # Price: Amount of Foreign per 1 EUR.
        # Rate: Price
        pair = f"EUR{to_currency}=X"
        inverse = False
    elif to_currency == "EUR":
        # Converting Foreign -> EUR (e.g. for Holdings Valution)
        # Pair: EUR{from_currency}=X
        # Price: Amount of Foreign per 1 EUR.
        # Rate: 1 / Price
        pair = f"EUR{from_currency}=X"
        inverse = True
        
    if pair:
        try:
            ticker = yf.Ticker(pair)
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                price = Decimal(str(hist['Close'].iloc[-1]))
                if price > 0:
                    if inverse:
                        rate = Decimal('1.0') / price
                    else:
                        rate = price
                    
                    _forex_cache[cache_key] = (rate, datetime.now())
                    save_cache()
                    return rate
            else:
                pass
        except Exception as e:
            logger.debug(f"[FOREX] Error fetching {pair}: {e}")

    # 5. Fallback
    logger.warning(f"[FOREX] Using fallback rate for {from_currency} -> {to_currency}")
    
    if to_currency == "EUR" and from_currency in FALLBACK_RATES:
        return FALLBACK_RATES[from_currency]
        
    if from_currency == "EUR" and to_currency in FALLBACK_RATES:
        # Fallback rates are Value of 1 UNIT in EUR.
        # So 1 USD = 0.95 EUR.
        # 1 EUR = 1 / 0.95 USD.
        val_in_eur = FALLBACK_RATES[to_currency]
        if val_in_eur > 0:
            return Decimal('1.0') / val_in_eur

    return Decimal('1.0') # Worst case

def get_rates_for_currencies(currencies: list) -> dict:
    """Batch fetch/get rates for a list of currencies."""
    results = {}
    for c in set(currencies):
        if c == 'EUR':
            results[c] = Decimal('1.0')
        else:
            results[c] = get_exchange_rate(c, 'EUR')
            
            # Special case: add 'GBp' (Pence) derived from GBP automatically if GBP is requested?
            # Or assume caller asks for what they need.
            if c == 'GBP':
                results['GBp'] = results['GBP'] / 100
                
    return results
