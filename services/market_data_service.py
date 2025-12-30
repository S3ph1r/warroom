
import requests
import yfinance as yf
from typing import List, Dict

# Yahoo Finance Autocomplete API
# Used by many libraries, reliable for search suggestions
SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

def search_market_symbol(query: str) -> List[Dict]:
    """
    Searches for a symbol (Ticker, Name, ISIN) on Yahoo Finance.
    Returns a list of candidates.
    """
    if not query or len(query) < 2:
        return []
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        params = {
            'q': query,
            'quotesCount': 10,
            'newsCount': 0,
            'enableFuzzyQuery': 'false',
            'quotesQueryId': 'tss_match_phrase_query'
        }
        
        response = requests.get(SEARCH_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = []
        if 'quotes' in data:
            for q in data['quotes']:
                # Filter out irrelevant types if needed, but option/future might be useful
                results.append({
                    "ticker": q.get('symbol'),
                    "name": q.get('shortname') or q.get('longname'),
                    "exchange": q.get('exchange'),
                    "type": q.get('quoteType'),
                    "score": q.get('score', 0)
                })
                
        return results
        
    except Exception as e:
        print(f"Market Search Error: {e}")
        return []

import re

def get_asset_details(ticker: str) -> Dict:
    """
    Fetches detailed info for a specific ticker to populate fields (Price, Name, ISIN).
    If ticker looks like an ISIN, attempts to resolve it via search first.
    """
    try:
        from services.price_service_v5 import clean_ticker, isin_to_yahoo_ticker
        
        # 0. Clean the ticker first
        ticker = clean_ticker(ticker)

        # 1. Check if input is likely an ISIN
        if re.match(r'^[A-Z]{2}[A-Z0-9]{9}\d$', ticker):
            # Try to resolve via OpenFIGI/Logic first
            resolved = isin_to_yahoo_ticker(ticker, ticker)
            if resolved and resolved != ticker:
                ticker = resolved
            else:
                # Fallback to Yahoo Search for ISIN
                candidates = search_market_symbol(ticker)
                if candidates:
                    # Pick the first candidate that looks like a valid ticker
                    best_match = candidates[0]['ticker']
                    for c in candidates:
                        if c['ticker'] != ticker:
                            best_match = c['ticker']
                            break
                    ticker = best_match

        t = yf.Ticker(ticker)
        
        # 1. Try fast_info (newer, faster, often more reliable)
        price = 0.0
        currency = "EUR"
        
        try:
            if hasattr(t, 'fast_info'):
                price = t.fast_info.last_price
                currency = t.fast_info.currency
        except:
            pass
            
        # 2. Fallback to info
        info = {}
        try:
             info = t.info
        except:
             pass # Info fetch commonly fails on strict networks or rate limits

        if not price:
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or info.get('navPrice') or 0
        
        if not currency and 'currency' in info:
             currency = info['currency']

        # 3. Fallback to history (Last resort)
        if not price:
            try:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            except:
                pass

        # Name fallback
        name = info.get('shortName') or info.get('longName') or ticker
        
        return {
            "ticker": ticker,
            "name": name,
            "price": float(price) if price else 0.0,
            "currency": currency,
            "isin": info.get('isin') # YF sometimes provides this, often not for US stocks
        }
    except Exception as e:
        print(f"Asset Details Error: {e}")
        return None
