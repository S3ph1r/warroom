"""
Real-Time Price Service v3
==========================
Cascading price validation:
1. Try alternative sources for EU ETFs
2. Try specific ticker mappings  
3. Validate against original price (sanity check)
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import time

import requests
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding


# Crypto symbol mapping
CRYPTO_MAP = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'DOT': 'polkadot',
    'XRP': 'ripple', 'BNB': 'binancecoin', 'AVAX': 'avalanche-2',
    '1INCH': '1inch', 'POL': 'matic-network', 'MATIC': 'matic-network',
    'IOTA': 'iota', 'HBAR': 'hedera-hashgraph', 'TON': 'the-open-network',
    'TRX': 'tron', 'FET': 'fetch-ai', 'PENGU': 'pudgy-penguins',
    'MOVE': 'movement', 'USUAL': 'usual', 'PNUT': 'peanut-the-squirrel',
    'ENA': 'ethena', 'BIO': 'biconomy', 'VANA': 'vana', 'THE': 'thena',
    'IO': 'io-net', '1000CAT': 'simons-cat', 'GALA': 'gala',
    'SAND': 'the-sandbox', 'MANA': 'decentraland', 'BB': 'bouncbit',
}

# ISIN to Yahoo ticker mapping for problematic ETFs
ETF_ISIN_TO_TICKER = {
    'IE00B4L5Y983': 'SWDA.MI',    # iShares Core MSCI World - Milan
    'IE00B4L5YC18': 'IEMA.MI',    # iShares MSCI Emerging Markets
    'IE00BGV5VN51': 'XAIX.DE',    # Xtrackers AI & Big Data
    'IE000M7V94E1': 'NUCL.DE',    # VanEck Uranium
    'IE00BJ5JPG56': 'ICGA.MI',    # iShares MSCI China A
    'IE00BF16M727': 'ISPY.L',     # iShares Cyber Security
    'IE00B42NKQ00': 'IUSE.MI',    # iShares S&P 500 Energy
    'IE00BMYDM794': 'HTWO.L',     # L&G Hydrogen Economy
    'IE00B0M63516': 'IBZL.MI',    # iShares MSCI Brazil
}

# Stock ticker corrections
STOCK_TICKER_MAP = {
    # Xiaomi - different tickers
    '1810': '1810.HK',
    '3CP': '1810.HK',
    # Others
    'RBOT': 'XBOT',
    'XBOT': 'XBOT',
}


def get_usd_to_eur_rate() -> Decimal:
    """Get current USD to EUR exchange rate."""
    try:
        eurusd = yf.Ticker('EURUSD=X')
        hist = eurusd.history(period='1d')
        if not hist.empty:
            return Decimal(str(round(1 / hist['Close'].iloc[-1], 4)))
    except:
        pass
    return Decimal('0.96')


def get_crypto_prices(symbols: list) -> dict:
    """Get crypto prices from CoinGecko API in EUR."""
    prices = {}
    ids = []
    symbol_to_id = {}
    
    for sym in symbols:
        cg_id = CRYPTO_MAP.get(sym.upper())
        if cg_id:
            ids.append(cg_id)
            symbol_to_id[cg_id] = sym
    
    if not ids:
        return prices
    
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=eur"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for cg_id, price_data in data.items():
                symbol = symbol_to_id.get(cg_id)
                if symbol and 'eur' in price_data:
                    prices[symbol] = Decimal(str(price_data['eur']))
    except Exception as e:
        print(f"  [WARN] CoinGecko: {e}")
    
    return prices


def try_get_price(ticker: str) -> tuple:
    """Try to get price from Yahoo Finance. Returns (price, success)."""
    if not ticker:
        return None, False
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            price = Decimal(str(round(hist['Close'].iloc[-1], 4)))
            return price, True
    except:
        pass
    
    return None, False


def get_stock_price_cascading(ticker: str, isin: str, original_price: Decimal, usd_to_eur: Decimal) -> tuple:
    """
    Get stock price using cascading strategy:
    1. Try specific ETF/stock ticker mapping
    2. Try Yahoo with ISIN-derived ticker
    3. Try Yahoo with raw ticker
    4. Validate result against original price
    
    Returns: (price_eur, yahoo_ticker_used, source)
    """
    attempts = []
    
    # Strategy 1: Check if we have a known ISIN mapping
    if isin and isin in ETF_ISIN_TO_TICKER:
        mapped_ticker = ETF_ISIN_TO_TICKER[isin]
        price, success = try_get_price(mapped_ticker)
        if success:
            attempts.append((price, mapped_ticker, 'ETF_MAP'))
    
    # Strategy 2: Check stock ticker mapping
    if ticker in STOCK_TICKER_MAP:
        mapped_ticker = STOCK_TICKER_MAP[ticker]
        price, success = try_get_price(mapped_ticker)
        if success:
            attempts.append((price, mapped_ticker, 'STOCK_MAP'))
    
    # Strategy 3: Try raw ticker
    price, success = try_get_price(ticker)
    if success:
        # Convert USD to EUR for US stocks
        if isin and isin.startswith('US'):
            price = price * usd_to_eur
        attempts.append((price, ticker, 'DIRECT'))
    
    # Strategy 4: Try ticker with exchange suffix based on ISIN country
    if isin and len(isin) >= 2:
        country = isin[:2]
        suffixes = {
            'IE': ['.L', '.MI', '.AS'],  # Ireland - try London, Milan, Amsterdam
            'NL': ['.AS'],               # Netherlands
            'FR': ['.PA'],               # France
            'DE': ['.DE'],               # Germany
            'IT': ['.MI'],               # Italy
            'DK': ['.CO'],               # Denmark
            'KY': [''],                  # Cayman (usually US ADR)
        }
        for suffix in suffixes.get(country, []):
            test_ticker = f"{ticker}{suffix}"
            price, success = try_get_price(test_ticker)
            if success:
                attempts.append((price, test_ticker, f'SUFFIX_{suffix}'))
                break
    
    # Validate and select best price
    if not attempts:
        return None, ticker, 'FAILED'
    
    # If we have original price, validate against it (max 5x difference)
    if original_price and original_price > 0:
        for price, used_ticker, source in attempts:
            ratio = float(price / original_price) if original_price > 0 else 999
            if 0.1 <= ratio <= 10:  # Price within 10x of original
                return price, used_ticker, source
        
        # All attempts failed validation - return original
        return original_price, ticker, 'KEPT_ORIGINAL'
    
    # No original price - use first successful attempt
    return attempts[0]


def update_all_prices():
    """Update all holdings with current prices."""
    print("=" * 70)
    print("UPDATING PRICES (v3 - Cascading Validation)")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    session = SessionLocal()
    holdings = session.query(Holding).filter(Holding.asset_type != 'CASH').all()
    
    # Get USD to EUR rate
    print("\nFetching USD/EUR exchange rate...")
    usd_to_eur = get_usd_to_eur_rate()
    print(f"  USD to EUR: {usd_to_eur:.4f}")
    
    crypto_holdings = [h for h in holdings if h.asset_type == 'CRYPTO']
    stock_holdings = [h for h in holdings if h.asset_type in ['STOCK', 'ETF']]
    
    updated = 0
    failed = 0
    kept_original = 0
    
    # Update crypto
    print(f"\n[CRYPTO] Updating {len(crypto_holdings)} holdings...")
    crypto_symbols = list(set(h.ticker for h in crypto_holdings))
    crypto_prices = get_crypto_prices(crypto_symbols)
    
    for h in crypto_holdings:
        price = crypto_prices.get(h.ticker.upper())
        if price:
            h.current_price = price
            h.current_value = h.quantity * price
            h.last_updated = datetime.now()
            updated += 1
            print(f"  [OK] {h.ticker:<10} | EUR {price:>10.4f} | Value: EUR {h.current_value:>10.2f}")
        else:
            failed += 1
            print(f"  [--] {h.ticker:<10} | No price")
    
    session.commit()
    
    # Update stocks
    print(f"\n[STOCKS] Updating {len(stock_holdings)} holdings...")
    
    for h in stock_holdings:
        original_price = h.current_price or Decimal('0')
        price, used_ticker, source = get_stock_price_cascading(
            h.ticker, h.isin, original_price, usd_to_eur
        )
        
        if price and source != 'FAILED':
            h.current_price = price
            h.current_value = h.quantity * price
            h.last_updated = datetime.now()
            
            if source == 'KEPT_ORIGINAL':
                kept_original += 1
                print(f"  [==] {h.ticker:<10} | Kept original EUR {price:>8.2f} (validation failed)")
            else:
                updated += 1
                print(f"  [OK] {h.ticker:<10} ({used_ticker:<12}) | EUR {price:>8.2f} | {source}")
        else:
            failed += 1
            print(f"  [--] {h.ticker:<10} | No valid price")
        
        time.sleep(0.2)
    
    session.commit()
    session.close()
    
    print(f"\n" + "=" * 70)
    print(f"SUMMARY")
    print(f"=" * 70)
    print(f"  Updated:        {updated}")
    print(f"  Kept Original:  {kept_original}")
    print(f"  Failed:         {failed}")
    print(f"  Total:          {updated + kept_original + failed}")
    print(f"=" * 70)
    
    return updated


if __name__ == "__main__":
    update_all_prices()
