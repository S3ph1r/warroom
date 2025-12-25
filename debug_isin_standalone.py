import yfinance as yf

def get_asset_details(ticker: str):
    """
    Fetches detailed info for a specific ticker to populate fields (Price, Name, ISIN).
    """
    print(f"--- Fetching for {ticker} ---")
    try:
        t = yf.Ticker(ticker)
        
        # 1. Try fast_info
        price = 0.0
        currency = "EUR"
        
        try:
            if hasattr(t, 'fast_info'):
                price = t.fast_info.last_price
                currency = t.fast_info.currency
                print(f"Fast Info Price: {price}, Currency: {currency}")
        except Exception as e:
            print(f"Fast Info failed: {e}")
            pass
            
        # 2. Fallback to info
        info = {}
        try:
             info = t.info
             print(f"Info keys: {list(info.keys())[:5]}...")
        except Exception as e:
             print(f"Info fetch failed: {e}")
             pass 

        if not price:
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or info.get('navPrice') or 0
        
        if not currency and 'currency' in info:
             currency = info['currency']

        # 3. Fallback to history
        if not price:
            try:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    print(f"History Price: {price}")
            except Exception as e:
                print(f"History failed: {e}")
                pass

        name = info.get('shortName') or info.get('longName') or ticker
        
        return {
            "ticker": ticker,
            "name": name,
            "price": float(price) if price else 0.0,
            "currency": currency,
            "isin": info.get('isin')
        }
    except Exception as e:
        print(f"Asset Details Error: {e}")
        return None

# Test Cases
print(get_asset_details("US26740W1099"))
print(get_asset_details("NVDA"))
