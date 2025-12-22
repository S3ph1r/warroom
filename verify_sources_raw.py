
import json
import asyncio
from intelligence.scrapers.rss_scraper import RSSScraper
from intelligence.scrapers.youtube_scraper import YoutubeScraper

def verify_all_sources():
    print("🚀 STARTING RAW SOURCE VERIFICATION")
    print("="*50)
    
    # Load Sources
    with open('data/sources.json', 'r') as f:
        config = json.load(f)
        
    # 1. RSS FEEDS
    print(f"\n📡 VERIFYING {len(config.get('rss_feeds', []))} RSS FEEDS")
    print("-" * 30)
    rss_scraper = RSSScraper()
    
    for url, name in config.get('rss_feeds', []):
        try:
            print(f"👉 Connecting to: {name}")
            items = rss_scraper.fetch(url, name)
            print(f"   ✅ Status: OK | Found {len(items)} items")
            if items:
                print(f"   Sample: {items[0]['title']}")
        except Exception as e:
            print(f"   ❌ Status: FAILED | Error: {e}")
            
    # 2. YOUTUBE CHANNELS
    print(f"\n📺 VERIFYING {len(config.get('youtube_channels', []))} YOUTUBE CHANNELS")
    print("-" * 30)
    yt_scraper = YoutubeScraper()
    
    channels = config.get('youtube_channels', [])
    for ch in channels:
        # Handle dict vs string
        if isinstance(ch, dict):
            handle = ch['handle']
            keyword = ch.get('filter_keyword')
        else:
            handle = ch
            keyword = None
            
        display_name = f"{handle} [Filter: {keyword}]" if keyword else handle
        
        try:
            print(f"👉 Scanning: {display_name}")
            # Fetch just a few to verify connectivity
            videos = yt_scraper.fetch_channel_updates(handle, limit=3, filter_keyword=keyword)
            print(f"   ✅ Status: OK | Found {len(videos)} MATCHING videos")
            if videos:
                print(f"   Sample: {videos[0]['title']}")
        except Exception as e:
            print(f"   ❌ Status: FAILED | Error: {e}")
            
    print("\n" + "="*50)
    print("🏁 VERIFICATION COMPLETE")

if __name__ == "__main__":
    verify_all_sources()
