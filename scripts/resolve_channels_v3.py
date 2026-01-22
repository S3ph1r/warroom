import requests
import re

def get_channel_id(handle):
    url = f"https://www.youtube.com/{handle}"
    # Cookies to bypass consent
    cookies = {
        'CONSENT': 'YES+cb.20230531-07-p0.en+FX+0',
        'SOCS': 'CAESEwgDEgk0ODEyMjk3MjQaAmVuIAEaBgiA_LyaBg'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        # Check if we are still on consent page
        if "consent.youtube.com" in resp.url:
            print("  Still redirected to consent page.")
            return None
            
        # Try to find channel ID
        # Pattern 1: channelId
        match = re.search(r'"channelId":"(UC[\w-]+)"', resp.text)
        if match:
            return match.group(1)
        
        # Pattern 2: externalId
        match = re.search(r'"externalId":"(UC[\w-]+)"', resp.text)
        if match:
            return match.group(1)
            
        # Pattern 3: content="UC..."
        match = re.search(r'itemprop="channelId" content="(UC[\w-]+)"', resp.text)
        if match:
            return match.group(1)
            
        # Pattern 4: RSS link
        match = re.search(r'channel_id=(UC[\w-]+)', resp.text)
        if match:
            return match.group(1)
            
        print("  No ID found in page content.")
        
    except Exception as e:
        print(f"  Error: {e}")
    return None

handles = ['@MarcoCasario', '@BlackBoxStocks', '@choramedia']
for h in handles:
    cid = get_channel_id(h)
    if cid:
        print(f"SUCCESS: {h} -> {cid}")
    else:
        print(f"FAILURE: {h}")
