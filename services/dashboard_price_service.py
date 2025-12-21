"""
Dashboard Price Service
=======================
Fetches real-time prices for dashboard display.
Does NOT update the database - prices are calculated live.
"""
import sys
from pathlib import Path
from decimal import Decimal
from functools import lru_cache
from datetime import datetime, timedelta
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

# Cache prices for 5 minutes to avoid hitting API rate limits
_price_cache = {}
_cache_ttl = timedelta(minutes=5)


# ISIN to Yahoo ticker mapping - MUST be complete for accurate prices
ISIN_TO_TICKER = {
    # ETFs
    'IE00B4L5Y983': 'SWDA.MI',    # iShares Core MSCI World
    'IE00B4L5YC18': 'IEMA.MI',    # iShares MSCI Emerging Markets
    'IE00BGV5VN51': 'XAIX.DE',    # Xtrackers AI & Big Data
    'IE00BMYDM794': 'HTWO.L',     # L&G Hydrogen Economy
    'IE00B42NKQ00': 'IUES.L',     # iShares S&P 500 Energy
    'IE00B0M63516': 'IBZL.MI',    # iShares MSCI Brazil
    'IE000M7V94E1': 'NUKL.DE',    # VanEck Uranium Nuclear
    
    # Italian stocks
    'IT0004056880': 'AMP.MI',     # Amplifon
    'IT0003128367': 'ENEL.MI',    # Enel
    'IT0003132476': 'ENI.MI',     # ENI
    'IT0000072618': 'ISP.MI',     # Intesa Sanpaolo
    'IT0005239360': 'UCG.MI',     # UniCredit
    'IT0001250932': 'HEX.MI',     # Hera
    'IT0005239881': 'STLA.MI',    # Stellantis (from Italy)
    'IT0000062072': 'LDO.MI',     # Leonardo
    'IT0005090300': 'WBD.MI',     # Webuild
    
    # Dutch stocks
    'NL0010273215': 'ASML.AS',    # ASML
    'NL0011585146': 'RACE.MI',    # Ferrari
    'NL00150001Q9': 'STLA.PA',    # Stellantis (from NL)
    
    # German stocks
    'DE0005313704': 'AFX.DE',     # Carl Zeiss Meditec
    'DE000BASF111': 'BAS.DE',     # BASF
    'DE0007164600': 'SAP.DE',     # SAP
    'DE0005557508': 'DTE.DE',     # Deutsche Telekom
    'DE0008404005': 'ALV.DE',     # Allianz
    
    # French stocks
    'FR0000121329': 'HO.PA',      # Thales
    'FR0000120271': 'TTE.PA',     # TotalEnergies
    'FR0000131104': 'BNP.PA',     # BNP Paribas
    'FR0000125486': 'OR.PA',      # L'Oreal
    
    # UK stocks
    'GB0007980591': 'BP.L',       # BP (London)
    'GB00B03MLX29': 'RR.L',       # Rolls Royce
    
    # US stocks (with EU ISINs or ADRs)
    'US0556221044': 'BP',         # BP ADR (US)
    
    # Hong Kong / China stocks
    'KYG017191142': '9988.HK',    # Alibaba (HK) - NOT BABA (different price)
    'KYG9830T1067': '1810.HK',    # Xiaomi
    'KYG070341048': '9888.HK',    # Baidu (HK) - NOT BIDU
    'KYG875721634': '0700.HK',    # Tencent
    'CNE100006M58': '000333.SZ',  # Midea Group
    
    # US stocks
    'US05606L1008': 'BYDDY',      # BYD ADR
    'US88160R1014': 'TSLA',       # Tesla
    'US90353T1007': 'UBER',       # Uber
    'US26740W1099': 'QBTS',       # D-Wave
    'US68389X1054': 'ORCL',       # Oracle
    'US2972842007': 'EL.PA',      # EssilorLuxottica (Paris listing)
    'US5949181045': 'MSFT',       # Microsoft
    'US0378331005': 'AAPL',       # Apple
    'US0231351067': 'AMZN',       # Amazon
    'US02079K1079': 'GOOGL',      # Alphabet
    'US67066G1040': 'NVDA',       # NVIDIA
    'US70450Y1038': 'PYPL',       # PayPal
    'US0846707026': 'BRK-B',      # Berkshire
    'US7475251036': 'QCOM',       # Qualcomm
    'US64110L1061': 'NFLX',       # Netflix
    'US0090661010': 'ABNB',       # Airbnb
    
    # Nordic stocks
    'DK0060534915': 'NOVO-B.CO',  # Novo Nordisk
    'FI0009000681': 'NOKIA.HE',   # Nokia
}

# Ticker corrections (when ISIN not available)
TICKER_MAP = {
    '3CP': '1810.HK',
    '1810': '1810.HK',
    'RGTI': 'RGTI',
    'RBOT': 'XBOT',
    'UAMY': 'UAMY',
    'GOOGL': 'GOOGL',
    'BIDU': '9888.HK',  # Use HK listing
    'BP': 'BP.L',       # UK listing by default
    'AMP': 'AMP.MI',    # Italian Amplifon
    'LDO': 'LDO.MI',    # Leonardo
    'WBD': 'WBD.MI',    # Webuild (not Warner Bros)
    'ETL': 'ETL.PA',    # Eutelsat
    'NOVOB': 'NOVO-B.CO',  # Novo Nordisk
    'NOKIA': 'NOKIA.HE',   # Nokia Helsinki
}

# CoinGecko IDs for crypto
CRYPTO_IDS = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano',
    'DOGE': 'dogecoin', 'DOT': 'polkadot', 'AVAX': 'avalanche-2',
    'TRX': 'tron', 'TON': 'the-open-network', 'IOTA': 'iota',
    'HBAR': 'hedera-hashgraph', 'FET': 'fetch-ai', 'POL': 'matic-network',
    '1INCH': '1inch', 'ENA': 'ethena', 'USDC': 'usd-coin',
    'USDT': 'tether', 'PNUT': 'peanut-the-squirrel', 'MOVE': 'move',
}

# Commodity prices (spot prices per oz in EUR)
COMMODITY_PRICES = {
    'XAU': Decimal('2600'),  # Gold ~€2,600/oz
    'XAG': Decimal('30'),    # Silver ~€30/oz
}


def _get_cached_price(key: str):
    """Get price from cache if not expired."""
    if key in _price_cache:
        price, timestamp = _price_cache[key]
        if datetime.now() - timestamp < _cache_ttl:
            return price
    return None


def _set_cached_price(key: str, price: Decimal):
    """Set price in cache."""
    _price_cache[key] = (price, datetime.now())


def get_stock_price(ticker: str, isin: str = None) -> Decimal:
    """Get current stock/ETF price in EUR."""
    # Check cache first
    cache_key = f"stock_{ticker}"
    cached = _get_cached_price(cache_key)
    if cached:
        return cached
    
    try:
        import yfinance as yf
        
        # Try ISIN mapping first
        yahoo_ticker = None
        if isin and isin in ISIN_TO_TICKER:
            yahoo_ticker = ISIN_TO_TICKER[isin]
        elif ticker in TICKER_MAP:
            yahoo_ticker = TICKER_MAP[ticker]
        else:
            yahoo_ticker = ticker
        
        # Fetch from Yahoo Finance
        stock = yf.Ticker(yahoo_ticker)
        hist = stock.history(period="1d")
        
        if not hist.empty:
            raw_price = Decimal(str(hist['Close'].iloc[-1]))
            
            # Get currency and convert to EUR
            currency = stock.info.get('currency', 'USD')
            
            # Handle minor currency units (pence, cents, etc.)
            # GBp = British pence (1/100 of GBP)
            # ILA = Israeli agorot (1/100 of ILS)
            if currency == 'GBp':
                raw_price = raw_price / Decimal('100')  # Convert pence to pounds
                currency = 'GBP'
            elif currency == 'ILA':
                raw_price = raw_price / Decimal('100')  # Convert agorot to ILS
                currency = 'ILS'
            
            # FX rates to EUR (approximate)
            fx_to_eur = {
                'EUR': Decimal('1.0'),
                'USD': Decimal('0.95'),
                'GBP': Decimal('1.18'),
                'HKD': Decimal('0.12'),
                'CNY': Decimal('0.13'),
                'ILS': Decimal('0.25'),
                'DKK': Decimal('0.134'),  # Danish Krone
                'SEK': Decimal('0.087'),  # Swedish Krona
                'NOK': Decimal('0.084'),  # Norwegian Krone
                'CHF': Decimal('1.06'),   # Swiss Franc
                'CAD': Decimal('0.66'),   # Canadian Dollar
                'AUD': Decimal('0.60'),   # Australian Dollar
                'JPY': Decimal('0.0063'), # Japanese Yen
            }
            
            rate = fx_to_eur.get(currency, Decimal('0.95'))  # Default to USD-like rate
            price_eur = raw_price * rate
            
            _set_cached_price(cache_key, price_eur)
            return price_eur
    except Exception as e:
        pass  # Silent fail, return None
    
    return None


def get_crypto_prices(symbols: list) -> dict:
    """Get crypto prices from CoinGecko in EUR."""
    # Check cache
    cache_key = "crypto_all"
    cached = _get_cached_price(cache_key)
    if cached:
        return {s: cached.get(s) for s in symbols if s in cached}
    
    try:
        # Map symbols to CoinGecko IDs
        ids = [CRYPTO_IDS.get(s.upper()) for s in symbols if s.upper() in CRYPTO_IDS]
        if not ids:
            return {}
        
        ids_str = ','.join([i for i in ids if i])
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=eur"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Map back to symbols
            result = {}
            for symbol in symbols:
                cg_id = CRYPTO_IDS.get(symbol.upper())
                if cg_id and cg_id in data:
                    result[symbol] = Decimal(str(data[cg_id]['eur']))
            
            _set_cached_price(cache_key, result)
            return result
    except Exception as e:
        pass
    
    return {}


def get_commodity_price(ticker: str) -> Decimal:
    """Get commodity price (gold/silver) in EUR per oz."""
    if ticker.upper() in COMMODITY_PRICES:
        return COMMODITY_PRICES[ticker.upper()]
    return None


def get_live_prices_for_holdings(holdings: list) -> dict:
    """
    Get live prices for all holdings.
    Returns dict: holding_id -> {live_price, live_value, pnl, pnl_pct}
    """
    result = {}
    
    # Group by asset type for batch processing
    stocks = [h for h in holdings if h.get('asset_type') in ['STOCK', 'ETF']]
    cryptos = [h for h in holdings if h.get('asset_type') == 'CRYPTO']
    commodities = [h for h in holdings if h.get('asset_type') == 'COMMODITY']
    cash = [h for h in holdings if h.get('asset_type') == 'CASH']
    
    # Process crypto in batch
    crypto_symbols = [h['ticker'] for h in cryptos]
    crypto_prices = get_crypto_prices(crypto_symbols) if crypto_symbols else {}
    
    for h in holdings:
        holding_id = h.get('id')
        ticker = h.get('ticker', '')
        isin = h.get('isin')
        asset_type = h.get('asset_type', '')
        quantity = Decimal(str(h.get('quantity', 0)))
        purchase_price = Decimal(str(h.get('purchase_price', 0) or h.get('current_price', 0) or 0))
        purchase_value = Decimal(str(h.get('current_value', 0)))
        
        live_price = None
        
        if asset_type in ['STOCK', 'ETF']:
            live_price = get_stock_price(ticker, isin)
        elif asset_type == 'CRYPTO':
            live_price = crypto_prices.get(ticker)
        elif asset_type == 'COMMODITY':
            live_price = get_commodity_price(ticker)
        elif asset_type == 'CASH':
            live_price = Decimal('1')
        
        if live_price:
            live_value = quantity * live_price
            cost_basis = quantity * purchase_price if purchase_price else purchase_value
            pnl = live_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis else Decimal('0')
            
            result[holding_id] = {
                'live_price': float(live_price),
                'live_value': float(live_value),
                'cost_basis': float(cost_basis),
                'pnl': float(pnl),
                'pnl_pct': float(pnl_pct),
            }
        else:
            # Fallback to stored values
            result[holding_id] = {
                'live_price': float(purchase_price) if purchase_price else 0,
                'live_value': float(purchase_value),
                'cost_basis': float(purchase_value),
                'pnl': 0,
                'pnl_pct': 0,
            }
    
    return result
