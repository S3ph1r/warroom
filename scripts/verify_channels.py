"""
Verify Channel IDs and Fix Altri Orienti
"""
import requests
import feedparser
import re

def check_channel(cid):
    print(f"Checking ID: {cid}...")
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    d = feedparser.parse(url)
    if d.entries:
        print(f"   ✅ Confirmed: {d.feed.title}")
        print(f"      Latest: {d.entries[0].title}")
        return d.feed.title
    else:
        print(f"   ❌ Invalid ID or Empty Feed")
        return None

def extract_from_url(url):
    print(f"Deep scan for {url}...")
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        # Try finding channelId in various forms
        # 1. itemprop="channelId" content="..."
        m1 = re.search(r'itemprop="channelId" content="(UC[\w-]+)"', resp.text)
        if m1: print(f"   Found via itemprop: {m1.group(1)}")
        
        # 2. "channelId":"..."
        m2 = re.findall(r'"channelId":"(UC[\w-]+)"', resp.text)
        print(f"   Found via json: {m2[:3]}") # Print first 3 matches
        
        # 3. Canonical URL
        m3 = re.search(r'link rel="canonical" href="https://www.youtube.com/channel/(UC[\w-]+)"', resp.text)
        if m3: print(f"   Found via canonical: {m3.group(1)}")
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    # 1. Verify what we found
    print("--- 1. VERIFYING EXTRACTED IDs ---")
    check_channel("UCZp2KqGRkO1goEAaxX5Huyg") # Casario?
    check_channel("UCsYN70T0gqR5U_xmWnZKcTQ") # Blackbox?
    
    # 2. Fix Altri Orienti
    print("\n--- 2. FIXING ALTRI ORIENTI ---")
    extract_from_url("https://www.youtube.com/watch?v=XtdOGZMa69E")

if __name__ == "__main__":
    main()
