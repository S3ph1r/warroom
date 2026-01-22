"""
Price Service v4 - Clean Architecture
======================================
Cascading price fetching with fallback to purchase_price.

Flow:
1. Try Yahoo Finance (stocks/ETFs) 
2. Try CoinGecko (crypto)
3. Try alternative sources
4. Fallback: use purchase_price from DB

All prices returned in EUR.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import requests
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================================
# PRICE CACHE (5 minutes TTL)
# ============================================================
_price_cache = {}
_cache_ttl = timedelta(minutes=5)


def _get_cached(key: str):
    if key in _price_cache:
        price, ts = _price_cache[key]
        if datetime.now() - ts < _cache_ttl:
            return price
    return None


def _set_cached(key: str, price: Decimal):
    _price_cache[key] = (price, datetime.now())


def clear_cache():
    """Clear all cached prices."""
    _price_cache.clear()


# ============================================================
# ISIN TO YAHOO TICKER MAPPING
# ============================================================
ISIN_TO_YAHOO = {
    # ETFs
    'IE00B4L5Y983': 'SWDA.MI',
    'IE00B4L5YC18': 'IEMA.MI',
    'IE00BGV5VN51': 'XAIX.DE',
    'IE00BMYDM794': 'HTWO.L',
    'IE00B42NKQ00': 'IUES.L',
    'IE00B0M63516': 'IBZL.MI',
    'IE000M7V94E1': 'NUKL.DE',
    
    # Italian stocks
    'IT0004056880': 'AMP.MI',      # Amplifon
    'IT0003128367': 'ENEL.MI',
    'IT0003132476': 'ENI.MI',
    'IT0000072618': 'ISP.MI',
    'IT0005239360': 'UCG.MI',
    'IT0000062072': 'LDO.MI',      # Leonardo
    'IT0005090300': 'WBD.MI',      # Webuild
    
    # Dutch stocks
    'NL0010273215': 'ASML.AS',
    'NL0011585146': 'RACE.MI',     # Ferrari
    
    # German stocks
    'DE0005313704': 'AFX.DE',      # Carl Zeiss
    
    # French stocks
    'FR0000121329': 'HO.PA',       # Thales
    
    # UK stocks
    'GB0007980591': 'BP.L',
    
    # US ADRs for China stocks
    'KYG017191142': '9988.HK',     # Alibaba HK
    'KYG9830T1067': '1810.HK',     # Xiaomi
    'KYG070341048': '9888.HK',     # Baidu HK
    'KYG875721634': '0700.HK',     # Tencent
    'CNE100006M58': '000333.SZ',   # Midea
    
    # US stocks
    'US88160R1014': 'TSLA',
    'US90353T1007': 'UBER',
    'US26740W1099': 'QBTS',
    'US68389X1054': 'ORCL',
    'US74767V1098': 'QS',          # QuantumScape
    'US70450Y1038': 'PYPL',
    'US0231351067': 'AMZN',
    'US02079K1079': 'GOOGL',
    'US67066G1040': 'NVDA',
    'US05606L1008': 'BYDDY',
    'US0567521085': 'BIDU',        # Baidu ADR
    
    # Nordic
    'DK0062498333': 'NOVO-B.CO',   # Novo Nordisk
    'DK0060534915': 'NOVO-B.CO',   # Novo Nordisk (alt ISIN)
}

# Ticker corrections (when ISIN not available)
TICKER_MAP = {
    '3CP': '1810.HK',
    'RGTI': 'RGTI',
    'UAMY': 'UAMY',
    'QS': 'QS',
    'AMP': 'AMP.MI',
    'BP': 'BP.L',
    'NOVOB': 'NOVO-B.CO',
    'BIDU': 'BIDU',
    'BABA': 'BABA',            # Alibaba ADR
    'LDO': 'LDO.MI',
    'WBD': 'WBD.MI',
    'ETL': 'ETL.PA',
    # BG Saxo ticker aliases
    'AHLA': 'BABA',            # Alibaba ADR (same as BABA)
    'NUCL': 'NUKL.DE',         # VanEck Uranium Nuclear
    'NOKIA': 'NOKIA.HE',       # Nokia Helsinki
    '02050': '2050.HK',        # Zhejiang Sanhua
    # These will use fallback (DB purchase_price) - no Yahoo equivalent
    # XBOT (Realbotix), CIBR, FLXI, ICGA, KSTR, SAI
}

# CoinGecko IDs
CRYPTO_IDS = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'BNB': 'binancecoin',
    'XRP': 'ripple',
    'ADA': 'cardano',
    'DOGE': 'dogecoin',
    'DOT': 'polkadot',
    'AVAX': 'avalanche-2',
    'TRX': 'tron',
    'TON': 'the-open-network',
    'IOTA': 'iota',
    'HBAR': 'hedera-hashgraph',
    'FET': 'fetch-ai',
    'POL': 'matic-network',
    '1INCH': '1inch',
    'ENA': 'ethena',
    'USDC': 'usd-coin',
    'USDT': 'tether',
    'PNUT': 'peanut-the-squirrel',
    'MOVE': 'movement',
    'IO': 'io-net',
}

# Fixed commodity prices (EUR per oz) - Revolut uses specific rates
COMMODITY_EUR_PRICES = {
    'XAU': Decimal('3660'),   # Gold - Revolut rate
    'XAG': Decimal('56'),     # Silver - Revolut rate
}

# FX rates to EUR (calibrated to match BG Saxo rates)
FX_TO_EUR = {
    'EUR': Decimal('1.0'),
    'USD': Decimal('0.853'),     # BG Saxo rate (was 0.95)
    'GBP': Decimal('1.06'),      # Updated
    'GBp': Decimal('0.0106'),    # Pence to EUR (1/100 of GBP)
    'HKD': Decimal('0.11'),      # Updated
    'CNY': Decimal('0.12'),      # Updated
    'DKK': Decimal('0.134'),
    'SEK': Decimal('0.087'),
    'NOK': Decimal('0.084'),
    'CHF': Decimal('0.94'),      # Updated
    'CAD': Decimal('0.60'),      # Updated
}


# ============================================================
# PRICE FETCHING FUNCTIONS
# ============================================================

def get_yahoo_price(ticker: str, isin: str = None) -> tuple[Decimal, str]:
    """
    Get price from Yahoo Finance.
    Returns: (price_eur, source) or (None, None)
    """
    cache_key = f"yahoo_{isin or ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached, "cache"
    
    try:
        import yfinance as yf
        
        # Determine Yahoo ticker
        yahoo_ticker = None
        if isin and isin in ISIN_TO_YAHOO:
            yahoo_ticker = ISIN_TO_YAHOO[isin]
        elif ticker in TICKER_MAP:
            yahoo_ticker = TICKER_MAP[ticker]
        else:
            yahoo_ticker = ticker
        
        stock = yf.Ticker(yahoo_ticker)
        hist = stock.history(period="1d")
        
        if hist.empty:
            return None, None
        
        raw_price = Decimal(str(hist['Close'].iloc[-1]))
        currency = stock.info.get('currency', 'USD')
        
        # Convert to EUR
        fx_rate = FX_TO_EUR.get(currency, Decimal('0.95'))
        price_eur = raw_price * fx_rate
        
        _set_cached(cache_key, price_eur)
        return price_eur, f"Yahoo:{yahoo_ticker}"
        
    except Exception as e:
        logger.debug(f"Yahoo error for {ticker}: {e}")
        return None, None


def get_coingecko_prices(symbols: list) -> dict:
    """
    Get crypto prices from CoinGecko.
    Returns: {symbol: price_eur}
    """
    cache_key = "coingecko_batch"
    cached = _get_cached(cache_key)
    if cached:
        return {s: cached.get(s) for s in symbols if s in cached}
    
    try:
        # Map symbols to CoinGecko IDs
        id_map = {}
        for s in symbols:
            if s.upper() in CRYPTO_IDS:
                id_map[CRYPTO_IDS[s.upper()]] = s
        
        if not id_map:
            return {}
        
        ids_str = ','.join(id_map.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=eur"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        
        data = resp.json()
        result = {}
        for cg_id, symbol in id_map.items():
            if cg_id in data and 'eur' in data[cg_id]:
                result[symbol] = Decimal(str(data[cg_id]['eur']))
        
        _set_cached(cache_key, result)
        return result
        
    except Exception as e:
        logger.debug(f"CoinGecko error: {e}")
        return {}


def get_commodity_price(ticker: str) -> tuple[Decimal, str]:
    """Get commodity price (gold/silver)."""
    upper = ticker.upper()
    if upper in COMMODITY_EUR_PRICES:
        return COMMODITY_EUR_PRICES[upper], "Fixed:Revolut"
    return None, None


# ============================================================
# MAIN PRICE FUNCTION
# ============================================================

def get_price(ticker: str, isin: str, asset_type: str, fallback_price: Decimal = None) -> tuple[Decimal, str]:
    """
    Get price for any asset with cascading fallback.
    
    Args:
        ticker: Asset ticker
        isin: ISIN code (optional)
        asset_type: STOCK, ETF, CRYPTO, COMMODITY, CASH
        fallback_price: Price to use if all sources fail
    
    Returns:
        (price_eur, source) where source indicates where price came from
    """
    if asset_type == 'CASH':
        return Decimal('1'), 'Cash'
    
    if asset_type == 'COMMODITY':
        price, source = get_commodity_price(ticker)
        if price:
            return price, source
    
    if asset_type == 'CRYPTO':
        prices = get_coingecko_prices([ticker])
        if ticker in prices:
            return prices[ticker], 'CoinGecko'
    
    if asset_type in ('STOCK', 'ETF'):
        price, source = get_yahoo_price(ticker, isin)
        if price:
            return price, source
    
    # Fallback to purchase price
    if fallback_price and fallback_price > 0:
        return fallback_price, 'Fallback:PurchasePrice'
    
    return Decimal('0'), 'NotFound'


# ============================================================
# BATCH PROCESSING FOR DASHBOARD
# ============================================================

def get_live_values_for_holdings(holdings: list) -> dict:
    """
    Calculate live values for all holdings.
    
    Args:
        holdings: List of holding dicts from portfolio_service
        
    Returns:
        Dict: holding_id -> {live_price, live_value, cost_basis, pnl, pnl_pct, source}
    """
    result = {}
    
    # Batch fetch crypto prices
    crypto_tickers = [h['ticker'] for h in holdings if h.get('asset_type') == 'CRYPTO']
    crypto_prices = get_coingecko_prices(crypto_tickers) if crypto_tickers else {}
    
    for h in holdings:
        hid = h.get('id')
        ticker = h.get('ticker', '')
        isin = h.get('isin')
        asset_type = h.get('asset_type', '')
        quantity = Decimal(str(h.get('quantity', 0)))
        purchase_price = Decimal(str(h.get('purchase_price') or h.get('current_price') or 0))
        
        # Get live price
        if asset_type == 'CRYPTO' and ticker in crypto_prices:
            live_price = crypto_prices[ticker]
            source = 'CoinGecko'
        else:
            live_price, source = get_price(ticker, isin, asset_type, purchase_price)
        
        # Calculate values
        live_value = quantity * live_price
        cost_basis = quantity * purchase_price if purchase_price else Decimal('0')
        
        if cost_basis > 0:
            pnl = live_value - cost_basis
            pnl_pct = float(pnl / cost_basis * 100)
        else:
            pnl = Decimal('0')
            pnl_pct = 0.0
        
        result[hid] = {
            'live_price': float(live_price),
            'live_value': float(live_value),
            'cost_basis': float(cost_basis),
            'pnl': float(pnl),
            'pnl_pct': pnl_pct,
            'source': source,
        }
    
    return result


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Quick test
    print("Testing Price Service v4...")
    
    # Test Yahoo
    price, src = get_yahoo_price('AAPL')
    print(f"AAPL: €{price:.2f} ({src})" if price else "AAPL: Not found")
    
    # Test with ISIN
    price, src = get_yahoo_price('AMP', 'IT0004056880')
    print(f"AMP.MI: €{price:.2f} ({src})" if price else "AMP: Not found")
    
    # Test CoinGecko
    prices = get_coingecko_prices(['BTC', 'ETH', 'SOL'])
    for sym, p in prices.items():
        print(f"{sym}: €{p:.2f}")
    
    # Test commodity
    price, src = get_commodity_price('XAU')
    print(f"Gold: €{price} ({src})")
