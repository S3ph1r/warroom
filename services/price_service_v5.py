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

# Manual ticker overrides (when OpenFIGI doesn't work or returns suboptimal results)
MANUAL_TICKER_MAP = {
    # Italian stocks
    'AMP': 'AMP.MI',          # Amplifon
    'Amplifon': 'AMP.MI',
    'AMPLIFON': 'AMP.MI',
    'LDO': 'LDO.MI',          # Leonardo
    'Leonardo': 'LDO.MI',
    'LEONARDO': 'LDO.MI',
    'RACE': 'RACE.MI',        # Ferrari (Milan)
    'Ferrari NV': 'RACE',
    'FERRARI NV': 'RACE',
    'WBD': 'WBD.MI',          # Webuild
    'CARL ZEISS MEDITEC': 'AFX.DE',
    
    # French stocks
    'ETL': 'ETL.PA',          # Eutelsat
    'ESSILORLUXOTTICA 1/2': 'EL.PA',
    'EL': 'EL.PA',            # EssilorLuxottica
    'THALES S.A.': 'HO.PA',
    
    # US stocks with weird names
    'RIVIAN AUTOMOT.A': 'RIVN',
    'RIVN': 'RIVN',
    'UBER TECH. DL-': 'UBER',
    'UBER TECH. DL-,00001': 'UBER',
    'SERVICENOW INC.': 'NOW',
    'ServiceNow Inc.': 'NOW',
    'TESLA INC.': 'TSLA',
    'TESLA INC. DL -,001': 'TSLA',
    'TESLA INC. DL': 'TSLA',
    'NVIDIA CORP.': 'NVDA',
    'NVIDIA Corp.': 'NVDA',
    
    # Chinese ADRs and Stocks
    'AHLA': 'BABA',           # BG Saxo Alibaba alias
    'ALIBABA GROUP HLDG L': 'BABA',
    'TENCENT HLDGS HD-': 'TCEHY',
    'TENCENT HLDGS HD-,00': 'TCEHY',
    'BAIDU INC. O.N.': 'BIDU',
    'BYD CO. LTD ADR/2 YC': 'BYDDY',
    'BYD COMPANY LTD - AD': 'BYDDY',
    # Scalable/Baader Mapping (ISIN/Name -> Correct Yahoo Ticker for Price)
    'KYG070341048': 'B1C.DE',    # Baidu (Xetra EUR)
    'Baidu Inc. O.N': 'B1C.DE',
    'KYG875721634': 'NNNd.DE',   # Tencent (Xetra EUR)
    'Tencent Hldgs': 'NNNd.DE',
    'US2972842007': 'ESLOY',     # EssilorLuxottica ADR (US)
    'EssilorLuxottica /O.': 'ESLOY',
    'CNE100006M58': '000333.SZ', # Midea Group (Shenzhen)
    'CNE100006M58': 'M0CL.F',    # Midea (Frankfurt) - trying this for EUR direct
    
    # European stocks
    'NOVOB': 'NOVO-B.CO',     # Novo Nordisk
    'NVO': 'NVO',
    'NOKIA': 'NOKIA.HE',      # Nokia Helsinki
    'Nokia Oyj': 'NOKIA.HE',
    'ZALANDO SE': 'ZAL.DE',
    
    # Hong Kong
    '02050': '2050.HK',       # Zhejiang Sanhua
    
    # ETFs
    'IE00B0M63516': 'ISBR.L', # iShares MSCI Brazil (London)
    'ISHSV-S+P500ENER.SEC': 'IXC', # iShares Energy ETF
    'iShares IV plc - iSh': 'IWDA.AS', # Guess for iShares World
    
    # Special cases
    'STLA': 'STLA.MI',        # Stellantis (Milan)
    'SWDA': 'SWDA.MI',        # iShares Core MSCI World
    'IWDA': 'IWDA.AS',
    'QRVO': 'QRVO',           # Qorvo (clean)
    'PANW': 'PANW',           # Palo Alto (clean)
    'CRSP': 'CRSP',           # CRISPR (clean)
    'PDD': 'PDD',             # Pinduoduo
    'VNET': 'VNET',           # VNET Group
}


def clean_ticker(ticker: str) -> str:
    """
    Remove MIC suffixes, exchange prefixes and noise from tickers.
    Examples:
        'ETL:xpar' -> 'ETL'
        'PYPL:xnas' -> 'PYPL'
        'NOVO NORDISK B A/S' -> 'NOVO-B' (manual map will catch the rest)
    """
    if not ticker:
        return ""
    
    # 1. Strip colon suffixes (MIC codes like :xnas, :xpar, :xmce)
    if ':' in ticker:
        ticker = ticker.split(':')[0]
    
    # 2. Strip leading $ (Saxo artifact)
    ticker = ticker.lstrip('$')
    
    # 3. Strip common trailing noise
    noise = [" DL-", " DL", " A/S", " O.N.", " ADR", " - ADR", " -", " CLASS ", " INC."]
    cleaned = ticker.strip()
    for n in noise:
        if cleaned.upper().endswith(n):
            cleaned = cleaned[: -len(n)].strip()
            
    return cleaned


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
    
    ENHANCED Strategy (ISIN-first):
    1. Check manual overrides first
    2. If ISIN present: Use OpenFIGI to get proper ticker (PRIORITY)
    3. Fallback: Derive from ISIN country prefix + original ticker
    4. Last resort: Return original ticker as-is
    """
    # Check manual overrides first
    if original_ticker and original_ticker in MANUAL_TICKER_MAP:
        return MANUAL_TICKER_MAP[original_ticker]
    
    # If no ISIN, return original ticker
    if not isin:
        return original_ticker
    
    # *** PRIORITY: Try OpenFIGI first when ISIN is available ***
    figi_result = get_ticker_from_isin(isin)
    if figi_result and figi_result.get('ticker'):
        ticker = figi_result['ticker']
        exchange = figi_result.get('exchange', '')
        
        exchange_suffixes = {
            'IM': '.MI', 'MI': '.MI', # Milan
            'GY': '.DE', 'DE': '.DE', 'ET': '.DE', # Germany
            'LN': '.L',  'LO': '.L', # London
            'PA': '.PA', 'FP': '.PA', # Paris
            'AS': '.AS', 'NA': '.AS', # Amsterdam
            'MC': '.MC', 'SM': '.MC', # Madrid
            'SW': '.SW', 'VX': '.SW', # Swiss
            'HK': '.HK', # Hong Kong
            'TK': '.T',  'JP': '.T', # Tokyo
            'CO': '.CO', 'DC': '.CO', # Copenhagen
            'ST': '.ST', 'SS': '.ST', # Stockholm
            'OL': '.OL', 'NO': '.OL', # Oslo
            'HE': '.HE', 'FH': '.HE', # Helsinki
        }
        
        # US exchanges don't need suffix in Yahoo
        if exchange in ['US', 'UN', 'UQ', 'UA', 'UW', 'NA', 'OQ']:
            if exchange == 'NA' and isin.startswith('NL'):
                # Handle edge case where NA is Amsterdam but OpenFIGI mapped as North America (rare)
                pass 
            else:
                logger.debug(f"ISIN {isin} -> {ticker} via OpenFIGI (US/NA)")
                return ticker
        
        suffix = exchange_suffixes.get(exchange.upper(), '')
        resolved = f"{ticker}{suffix}" if suffix else ticker
        logger.debug(f"ISIN {isin} -> {resolved} via OpenFIGI (Exch: {exchange})")
        return resolved
    
    # Fallback: Derive exchange from ISIN country prefix
    isin_prefix = isin[:2].upper() if isin else ''
    
    # EU ETFs (Ireland/Luxembourg) - prefer EUR-denominated exchanges
    if isin_prefix in ['IE', 'LU']:
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
    
    return original_ticker


def resolve_asset_info(isin: str, original_ticker: str = None) -> dict:
    """
    Resolve both name and Yahoo-compatible ticker for an asset.
    Used during ingestion to normalize data.
    """
    if not isin:
        return {"ticker": original_ticker, "name": "Unknown"}
        
    # Get proper ticker from our enhanced logic
    yahoo_ticker = isin_to_yahoo_ticker(isin, original_ticker)
    
    # Get name from OpenFIGI (cached)
    figi_data = get_ticker_from_isin(isin)
    resolved_name = figi_data.get('name', 'Unknown') if figi_data else "Unknown"
    
    # Clean up name (remove Bloomberg noise if any)
    if resolved_name and resolved_name != "Unknown":
        noise = ["-UNSP ADR", " ADR"]
        for n in noise:
            resolved_name = resolved_name.replace(n, "").strip()

    return {
        "ticker": yahoo_ticker,
        "name": resolved_name
    }


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
        
        # Clean ticker fallback (if original had junk like :xnas)
        cleaned_base = clean_ticker(ticker)
        if cleaned_base and cleaned_base != ticker:
            # Let logic re-resolve cleaned ticker
            cleaned_yahoo = isin_to_yahoo_ticker(isin, cleaned_base)
            if cleaned_yahoo not in tickers_to_try:
                tickers_to_try.append(cleaned_yahoo)

        # For EU ETFs, add fallback exchanges
        if is_eu_etf:
            base_ticker = cleaned_base.split('.')[0]
            for suffix in ['.MI', '.DE', '.L', '.AS']:
                fallback = f"{base_ticker}{suffix}"
                if fallback not in tickers_to_try:
                    tickers_to_try.append(fallback)
        
        logger.info(f"Fetching {isin or ticker}: attempting {tickers_to_try}")
        
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
            
            # ---------------------------------------------------------
            # SMART ADR LOGIC
            # Handle case where we hold an ADR (e.g. Ratio 0.5) but pricing finds the Underlying (Full Price).
            # Heuristic: If ISIN is US/KY (typical ADR) but Price Source is a foreign market ticker (.PA, .DE, .MI...)
            # ---------------------------------------------------------
            adr_ratio = h.get('adr_ratio')
            if adr_ratio and adr_ratio > 0 and adr_ratio != 1.0:
                 # Check specific ISIN prefixes common for ADRs
                 is_adr_isin = isin and (isin.startswith('US') or isin.startswith('KY'))
                 
                 # Check if resolved ticker looks like a foreign market listing
                 # Extract ticker from "Yahoo:EL.PA" or "AlphaVantage:BMW.DE"
                 source_ticker = source.split(':')[-1] if ':' in source else ''
                 
                 foreign_suffixes = ['.PA', '.DE', '.MI', '.L', '.AS', '.HK', '.T', '.CO', '.HE', '.ST', '.OL', '.MC', '.SW']
                 is_foreign_source = any(source_ticker.endswith(s) for s in foreign_suffixes)
                 
                 # If we are pricing an ADR using its foreign underlying -> Apply Ratio
                 if is_adr_isin and is_foreign_source:
                     # logger.info(f"📉 Applying ADR Ratio {adr_ratio} to {ticker} ({source_ticker}). Original: {live_price}")
                     live_price = live_price * Decimal(str(adr_ratio))
            
            # If fallback (DB Price), convert to EUR (as get_price handles live but not fallback conversion)
            if 'FALLBACK' in source and fx_rate != 1:
                live_price = live_price * fx_rate
            
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
