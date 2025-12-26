"""
Price Service v5 - Multi-Source with OpenFIGI
==============================================

Cascading price fetching:
1. OpenFIGI: ISIN → correct ticker for exchange
2. Yahoo Finance: primary price source
3. Alpha Vantage: backup for stocks
4. CoinGecko: crypto
5. Fallback: DB purchase_price (flagged in dashboard)

All prices returned in EUR.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import requests
import logging
import json
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================================
# CACHE (10 minutes TTL, File Persistent)
# ============================================================
CACHE_FILE = os.path.join(str(Path(__file__).parent.parent), "data", "prices_cache.json")
_cache_ttl = timedelta(minutes=10)

def _load_cache_from_disk():
    """Load cache from JSON file, converting types back."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                loaded = {}
                for k, v in data.items():
                    # Format: [value_float, timestamp_iso, change_pct_float]
                    # Backwards compatibility: if list len is 2, change_pct = 0.0
                    val = v[0]
                    ts_str = v[1]
                    change_pct = v[2] if len(v) > 2 else 0.0
                    
                    loaded[k] = (Decimal(str(val)), datetime.fromisoformat(ts_str), float(change_pct))
                return loaded
        except Exception as e:
            logger.warning(f"Failed to load price cache: {e}")
    return {}

def _save_cache_to_disk(cache):
    """Save cache to JSON file, serializing types."""
    try:
        data = {}
        for k, v in cache.items():
            val, ts, change_pct = v
            # Store as float for JSON, ISO for datetime
            data[k] = (float(val), ts.isoformat(), float(change_pct))
        
        # Ensure dir
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Failed to save price cache: {e}")

_price_cache = _load_cache_from_disk()
_figi_cache = {}  # Keep in-memory only for now

def _get_cached(cache: dict, key: str):
    if key in cache:
        value, ts, change_pct = cache[key]
        if datetime.now() - ts < _cache_ttl:
            return value, change_pct
        else:
            # Expired
            del cache[key]
    return None, 0.0


def _set_cached(cache: dict, key: str, value, change_pct=0.0):
    cache[key] = (value, datetime.now(), change_pct)
    # Persist only price cache
    if cache is _price_cache:
        _save_cache_to_disk(cache)


def clear_cache():
    """Clear all caches."""
    _price_cache.clear()
    _figi_cache.clear()


# ============================================================
# FX RATES TO EUR (Dynamic via Forex Service)
# ============================================================
from services.forex_service import get_exchange_rate, get_rates_for_currencies

# CoinGecko IDs
CRYPTO_IDS = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano',
    'DOGE': 'dogecoin', 'DOT': 'polkadot', 'AVAX': 'avalanche-2',
    'TRX': 'tron', 'TON': 'the-open-network', 'IOTA': 'iota',
    'HBAR': 'hedera-hashgraph', 'FET': 'fetch-ai', 'POL': 'matic-network',
    '1INCH': '1inch', 'ENA': 'ethena', 'USDC': 'usd-coin',
    'USDT': 'tether', 'PNUT': 'peanut-the-squirrel', 'MOVE': 'movement',
    'IO': 'io-net',
}

# Fixed commodity prices (EUR per oz) - calibrated to Revolut
# XAU: 0.19 oz = 700 EUR -> 3684 EUR/oz
# XAG: 3.35 oz = 190 EUR -> 56.72 EUR/oz
COMMODITY_PRICES = {
    'XAU': Decimal('3684'),   # Gold (Revolut rate)
    'XAG': Decimal('56.72'),  # Silver (Revolut rate)
}

# Manual ticker overrides (when OpenFIGI doesn't work)
MANUAL_TICKER_MAP = {
    'AHLA': 'BABA',           # BG Saxo Alibaba alias
    'NOVOB': 'NOVO-B.CO',     # Novo Nordisk
    'AMP': 'AMP.MI',          # Amplifon
    'LDO': 'LDO.MI',          # Leonardo
    'WBD': 'WBD.MI',          # Webuild
    'ETL': 'ETL.PA',          # Eutelsat
    'NOKIA': 'NOKIA.HE',      # Nokia Helsinki
    '02050': '2050.HK',       # Zhejiang Sanhua
    'RACE': 'RACE.MI',        # Ferrari (Milan)
    'STLA': 'STLA.MI',        # Stellantis (Milan)
    'IE00B0M63516': 'ISBR.L', # iShares MSCI Brazil (London)
    # BP uses NYSE ADR (USD) for Revolut, not BP.L (London GBp)
}


# ============================================================
# OPENFIGI - ISIN TO TICKER MAPPING
# ============================================================

def get_ticker_from_isin(isin: str) -> dict:
    """
    Use OpenFIGI API to get ticker information from ISIN.
    Returns: {'ticker': str, 'exchange': str, 'name': str} or None
    
    OpenFIGI is Bloomberg's free FIGI lookup service.
    """
    if not isin:
        return None
    
    # Check cache
    cached_data, _ = _get_cached(_figi_cache, isin)
    if cached_data:
        return cached_data
    
    try:
        url = "https://api.openfigi.com/v3/mapping"
        headers = {"Content-Type": "application/json"}
        
        # Request mapping for this ISIN
        payload = [{"idType": "ID_ISIN", "idValue": isin}]
        
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        if not data or not data[0].get('data'):
            return None
        
        # Get first result (often multiple exchanges)
        results = data[0]['data']
        
        # Prefer certain exchanges
        preferred_exchanges = ['US', 'NA', 'LN', 'GY', 'IM', 'PA', 'MC', 'AS', 'SW', 'HK']
        
        best_match = None
        for r in results:
            ticker = r.get('ticker', '')
            exchange = r.get('exchCode', '')
            
            if not best_match:
                best_match = r
            
            # Prefer US stocks for ADRs
            if exchange in preferred_exchanges:
                best_match = r
                break
        
        if best_match:
            result = {
                'ticker': best_match.get('ticker', ''),
                'exchange': best_match.get('exchCode', ''),
                'name': best_match.get('name', ''),
                'figi': best_match.get('figi', ''),
            }
            _set_cached(_figi_cache, isin, result)
            return result
        
    except Exception as e:
        logger.debug(f"OpenFIGI error for {isin}: {e}")
    
    return None


def isin_to_yahoo_ticker(isin: str, original_ticker: str = None, asset_type: str = None) -> str:
    """
    Convert ISIN to Yahoo Finance ticker format.
    
    Strategy:
    1. Check manual overrides first
    2. For EU ETFs (IE*/LU*): try .MI, .DE, .L suffixes (EUR preferred)
    3. For Italian stocks (IT*): use .MI
    4. For German stocks (DE*): use .DE
    5. Use OpenFIGI as fallback
    """
    # Check manual overrides first
    if original_ticker and original_ticker in MANUAL_TICKER_MAP:
        return MANUAL_TICKER_MAP[original_ticker]
    
    if not isin:
        return original_ticker
    
    # Derive exchange from ISIN country prefix
    isin_prefix = isin[:2].upper() if isin else ''
    
    # EU ETFs (Ireland/Luxembourg) - prefer EUR-denominated exchanges
    if isin_prefix in ['IE', 'LU']:
        # Try ticker with EUR exchanges first
        # Most BG Saxo ETFs are listed on MI (Italy) or DE (Germany)
        return f"{original_ticker}.MI" if original_ticker else original_ticker
    
    # Italian stocks
    if isin_prefix == 'IT':
        return f"{original_ticker}.MI" if original_ticker else original_ticker
    
    # German stocks  
    if isin_prefix == 'DE':
        return f"{original_ticker}.DE" if original_ticker else original_ticker
    
    # French stocks
    if isin_prefix == 'FR':
        return f"{original_ticker}.PA" if original_ticker else original_ticker
    
    # Dutch stocks
    if isin_prefix == 'NL':
        return f"{original_ticker}.AS" if original_ticker else original_ticker
    
    # UK stocks
    if isin_prefix == 'GB':
        return f"{original_ticker}.L" if original_ticker else original_ticker
    
    # Hong Kong stocks
    if isin_prefix == 'HK':
        return f"{original_ticker}.HK" if original_ticker else original_ticker
    
    # US stocks (no suffix needed)
    if isin_prefix == 'US':
        return original_ticker
    
    # Cayman Islands (often Chinese ADRs)
    if isin_prefix == 'KY':
        return original_ticker  # Usually US ADRs
    
    # Danish stocks
    if isin_prefix == 'DK':
        return f"{original_ticker}.CO" if original_ticker else original_ticker
    
    # Fallback: use OpenFIGI
    figi_result = get_ticker_from_isin(isin)
    if figi_result:
        ticker = figi_result['ticker']
        exchange = figi_result['exchange']
        
        exchange_suffixes = {
            'IM': '.MI', 'GY': '.DE', 'LN': '.L', 'PA': '.PA',
            'AS': '.AS', 'MC': '.MC', 'SW': '.SW', 'HK': '.HK',
            'TK': '.T', 'CO': '.CO', 'ST': '.ST', 'OL': '.OL', 'HE': '.HE',
        }
        
        if exchange in ['US', 'UN', 'UQ', 'UA', 'UW']:
            return ticker
        
        suffix = exchange_suffixes.get(exchange, '')
        return f"{ticker}{suffix}" if suffix else ticker
    
    return original_ticker


# ============================================================
# YAHOO FINANCE
# ============================================================

def get_yahoo_price(ticker: str, isin: str = None) -> tuple:
    """
    Get price from Yahoo Finance.
    Returns: (price_eur, source_string, success_bool, change_pct_1d)
    """
    cache_key = f"yahoo_{isin or ticker}"
    cached_price, cached_change = _get_cached(_price_cache, cache_key)
    if cached_price:
        return cached_price, "Yahoo (cached)", True, cached_change
    
    try:
        import yfinance as yf
        
        # Get primary ticker
        yahoo_ticker = isin_to_yahoo_ticker(isin, ticker)
        
        # Determine if EU ETF (might need fallback exchanges)
        isin_prefix = isin[:2].upper() if isin else ''
        is_eu_etf = isin_prefix in ['IE', 'LU']
        
        # Try primary ticker first
        tickers_to_try = [yahoo_ticker]
        
        # For EU ETFs, add fallback exchanges
        if is_eu_etf:
            base_ticker = ticker.split('.')[0]  # Remove any existing suffix
            for suffix in ['.MI', '.DE', '.L', '.AS']:
                fallback = f"{base_ticker}{suffix}"
                if fallback != yahoo_ticker and fallback not in tickers_to_try:
                    tickers_to_try.append(fallback)
        
        for try_ticker in tickers_to_try:
            stock = yf.Ticker(try_ticker)
            # Fetch 5d to ensure we have previous close even on Mondays/Holidays
            hist = stock.history(period="5d")
            
            if not hist.empty:
                current_close = Decimal(str(hist['Close'].iloc[-1]))
                
                # Calculate change pct
                prev_close = Decimal('0')
                if len(hist) >= 2:
                    prev_close = Decimal(str(hist['Close'].iloc[-2]))
                
                # Fallback to stock.info if hist only has 1 row (market just opened) or hist prev is missing
                if not prev_close or prev_close <= 0:
                    info_prev = stock.info.get('regularMarketPreviousClose') or stock.info.get('previousClose')
                    if info_prev:
                        prev_close = Decimal(str(info_prev))
                
                change_pct = 0.0
                if prev_close and prev_close > 0:
                    change_pct = float((current_close - prev_close) / prev_close * 100)
                
                currency = stock.info.get('currency', 'USD')
                
                # Convert to EUR using Forex Service
                fx_rate = get_exchange_rate(currency, 'EUR')
                price_eur = current_close * fx_rate
                
                _set_cached(_price_cache, cache_key, price_eur, change_pct)
                return price_eur, f"Yahoo:{try_ticker}", True, change_pct
        
        # All attempts failed
        return None, f"Yahoo:{yahoo_ticker} (no data)", False, 0.0
        
    except Exception as e:
        logger.debug(f"Yahoo error for {ticker}: {e}")
        return None, f"Yahoo:{ticker} (error)", False, 0.0


# ============================================================
# ALPHA VANTAGE (backup)
# ============================================================

def get_alphavantage_price(ticker: str, api_key: str = None) -> tuple:
    """
    Get price from Alpha Vantage.
    Returns: (price_eur, source_string, success_bool, change_pct_1d)
    """
    if not api_key:
        api_key = "demo"
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": api_key
        }
        
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None, "AlphaVantage (error)", False, 0.0
        
        data = resp.json()
        quote = data.get("Global Quote", {})
        
        if not quote or "05. price" not in quote:
            return None, "AlphaVantage (no data)", False, 0.0
        
        price_usd = Decimal(quote["05. price"])
        change_pct_str = quote.get("10. change percent", "0%").replace("%", "")
        change_pct = float(change_pct_str)
        
        # Convert from USD to EUR
        fx_rate = get_exchange_rate('USD', 'EUR')
        price_eur = price_usd * fx_rate
        
        return price_eur, f"AlphaVantage:{ticker}", True, change_pct
        
    except Exception as e:
        logger.debug(f"AlphaVantage error for {ticker}: {e}")
        return None, "AlphaVantage (error)", False, 0.0


# ============================================================
# COINGECKO (crypto)
# ============================================================

def get_coingecko_prices(symbols: list) -> dict:
    """
    Get crypto prices from CoinGecko.
    Returns dict: ticker -> {price: Decimal, change_24h: float}
    """
    # NO CACHING for now to simplify struct change, or separate cache key
    # cache_key = "coingecko_batch"
    
    try:
        id_map = {CRYPTO_IDS[s.upper()]: s for s in symbols if s.upper() in CRYPTO_IDS}
        if not id_map:
            return {}
        
        ids_str = ','.join(id_map.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=eur&include_24hr_change=true"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        
        data = resp.json()
        result = {}
        for cg_id, symbol in id_map.items():
            if cg_id in data and 'eur' in data[cg_id]:
                result[symbol] = {
                    'price': Decimal(str(data[cg_id]['eur'])),
                    'change_24h': float(data[cg_id].get('eur_24h_change', 0.0))
                }
        return result
        
    except Exception as e:
        logger.debug(f"CoinGecko error: {e}")
        return {}


# ============================================================
# MAIN CASCADING PRICE FUNCTION
# ============================================================

def get_price(ticker: str, isin: str, asset_type: str, 
              fallback_price: Decimal = None) -> tuple:
    """
    Returns: (price_eur, source_string, is_live_bool, change_pct_1d)
    """
    # CASH
    if asset_type == 'CASH':
        return Decimal('1'), 'Cash', True, 0.0
    
    # COMMODITIES
    if asset_type == 'COMMODITY':
        if ticker.upper() in COMMODITY_PRICES:
            # Fixed price, no daily change tracking in this simple version
            return COMMODITY_PRICES[ticker.upper()], f'Fixed:{ticker}', True, 0.0
    
    # CRYPTO - CoinGecko (Handled in batch usually, but singular here if called directly)
    if asset_type == 'CRYPTO':
        data = get_coingecko_prices([ticker])
        if ticker in data:
            return data[ticker]['price'], 'CoinGecko', True, data[ticker]['change_24h']
    
    # STOCKS/ETFs
    if asset_type in ('STOCK', 'ETF'):
        
        # 1. Yahoo + ISIN
        if isin:
            price, source, success, change = get_yahoo_price(ticker, isin)
            if success and price:
                return price, source, True, change
        
        # 2. Yahoo Ticker
        price, source, success, change = get_yahoo_price(ticker)
        if success and price:
            return price, source, True, change
        
        # 3. AlphaVantage
        price, source, success, change = get_alphavantage_price(ticker)
        if success and price:
            return price, source, True, change
    
    # FALLBACK
    if fallback_price and fallback_price > 0:
        return fallback_price, 'FALLBACK:DB', False, 0.0
    
    return Decimal('0'), 'NOT_FOUND', False, 0.0


def get_live_price_for_ticker(ticker: str, asset_type: str = "STOCK") -> dict:
    """
    Simple helper for alert engine - get live price for a single ticker.
    Returns: {"price": float, "change_pct": float, "source": str} or None
    """
    try:
        price, source, is_live, change_pct = get_price(ticker, None, asset_type, None)
        
        if price and price > 0:
            return {
                "price": float(price),
                "change_pct": change_pct,
                "source": source,
                "is_live": is_live
            }
    except Exception as e:
        logger.error(f"get_live_price_for_ticker error for {ticker}: {e}")
    
    return None


# ============================================================
# BATCH PROCESSING FOR DASHBOARD
# ============================================================

def get_live_values_for_holdings(holdings: list) -> dict:
    """
    Calculate live values, P&L, and Daily change.
    """
    result = {}
    
    # Batch fetch crypto prices first
    crypto_tickers = [h['ticker'] for h in holdings if h.get('asset_type') == 'CRYPTO']
    crypto_data = get_coingecko_prices(crypto_tickers) if crypto_tickers else {}
    
    # Pre-fetch exchange rates for all holding currencies
    all_currencies = list(set([h.get('currency', 'EUR') for h in holdings]))
    fx_rates = get_rates_for_currencies(all_currencies)
    
    for h in holdings:
        hid = h.get('id')
        ticker = h.get('ticker', '')
        isin = h.get('isin')
        asset_type = h.get('asset_type', '')
        quantity = Decimal(str(h.get('quantity', 0)))
        purchase_price = Decimal(str(h.get('purchase_price') or h.get('current_price') or 0))
        
        # Get live data
        day_change_pct = 0.0
        
        # Get FX Rate first
        h_currency = h.get('currency', 'EUR')
        fx_rate = fx_rates.get(h_currency, Decimal('1.0'))
        
        # Handle GBp special case
        if h_currency == 'GBp' and 'GBp' not in fx_rates and 'GBP' in fx_rates:
             fx_rate = fx_rates['GBP'] / 100
             
        # Logic dispatcher
        if asset_type == 'CASH':
            # CASH: Cost = Value = Quantity * FX Rate (in EUR)
            # Price of 1 unit is the FX rate
            live_price = float(fx_rate)
            live_value = quantity * fx_rate
            cost_basis = live_value # Cash has 0 P&L by definition in this model (or we track currency P&L separately?)
                                    # User wants "Net Invested", so Cash is Invested Capital. Cost = Value.
            source = "FX_RATE"
            is_live = True
            day_change_pct = 0.0 # Could be improved with FX daily change
            purchase_price = Decimal('1') # Nominal
            
        elif asset_type == 'CRYPTO' and ticker in crypto_data:
            live_price = crypto_data[ticker]['price']
            day_change_pct = crypto_data[ticker]['change_24h']
            source = 'CoinGecko'
            is_live = True
            
            live_value = quantity * live_price
            purchase_price_eur = purchase_price * fx_rate
            cost_basis = quantity * purchase_price_eur if purchase_price else Decimal('0')
            
        else:
            live_price, source, is_live, day_change_pct = get_price(ticker, isin, asset_type, purchase_price)
            
            live_value = quantity * live_price
            purchase_price_eur = purchase_price * fx_rate
            cost_basis = quantity * purchase_price_eur if purchase_price else Decimal('0')
        
        # Total P&L
        if cost_basis > 0:
            pnl = live_value - cost_basis
            pnl_pct = float(pnl / cost_basis * 100)
        else:
            pnl = Decimal('0')
            pnl_pct = 0.0
            
        # Daily P&L (Approximate: current_value * change / (100 + change))
        # Logic: Current = Prev * (1 + pct/100) -> Prev = Current / (1 + pct/100)
        # Day P&L = Current - Prev
        day_pl = 0.0
        if is_live and live_value > 0:
            try:
                prev_value = float(live_value) / (1 + (day_change_pct / 100.0))
                day_pl = float(live_value) - prev_value
            except:
                day_pl = 0.0
        
        result[hid] = {
            'live_price': float(live_price),
            'live_value': float(live_value),
            'cost_basis': float(cost_basis),
            'pnl': float(pnl),
            'pnl_pct': pnl_pct,
            'source': source,
            'is_live': is_live,
            'day_change_pct': day_change_pct,
            'day_pl': day_pl,
            # Multi-currency support
            'native_current_value': float(live_value / fx_rate) if fx_rate and fx_rate > 0 else float(live_value),
            'exchange_rate_used': float(fx_rate),
            'currency': h_currency
        }
    
    return result


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    print("Testing Price Service v5 with Dynamic Forex...")
    print("=" * 60)
    
    # Test OpenFIGI lookup
    test_isins = [
        ('IT0004056880', 'AMP', 'Amplifon'),
        ('IE00B42NKQ00', 'CIBR', 'iShares something'),
        ('US0231351067', 'AMZN', 'Amazon'),
    ]
    
    print("\n[1] OpenFIGI ISIN Lookup:")
    for isin, ticker, name in test_isins:
        result = get_ticker_from_isin(isin)
        if result:
            print(f"  {isin} -> {result['ticker']} ({result['exchange']}) - {result.get('name', '')[:30]}")
        else:
            print(f"  {isin} -> NOT FOUND")
    
    print("\n[2] Yahoo Price Fetch (with FX conversion):")
    for isin, ticker, name in test_isins:
        price, source, success, change = get_yahoo_price(ticker, isin)
        status = "OK" if success else "FAIL"
        price_str = f"{price:.2f}" if price else "0"
        print(f"  {name}: EUR {price_str} [{source}] {status}")
