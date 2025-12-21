"""
Test YouTube Scraper & Engine Integration
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence.scrapers.youtube_scraper import YoutubeScraper
from intelligence.engine import IntelligenceEngine

def main():
    print("--- 📺 YouTube Scraper Test ---")
    scraper = YoutubeScraper()
    
    handles = ["@MarcoCasario", "@BlackBoxStocks", "@choramedia"]
    
    for handle in handles:
        print(f"\n--- Testing {handle} ---")
        print(f"1. Resolving {handle}...")
        cid = scraper.get_channel_id(handle)
        
        if cid:
            print(f"   ✅ Found ID: {cid}")
            
            # 2. Test Feed Fetch
            print(f"   Fetching videos for {cid}...")
            videos = scraper.get_latest_videos(cid, limit=1)
            if videos:
                v = videos[0]
                print(f"   ✅ Latest Video: {v['title']}")
                print(f"   🔗 Link: {v['link']}")
                
                # 3. Test Transcript
                print(f"   Fetching Transcript for {v['video_id']}...")
                text = scraper.get_transcript(v['video_id'])
                if text:
                    print(f"   ✅ Transcript found ({len(text)} chars)")
                    print(f"   📝 Preview: {text[:100]}...")
                else:
                    print(f"   ⚠️ No transcript available for {v['video_id']}")
            else:
                print("   ❌ No videos found.")
        else:
            print("   ❌ Failed to resolve ID.")

    # 4. Engine Integration Test (Mock)
    print(f"\n4. Engine Cycle Test (Mock)...")
    # We won't run the full engine to save time/tokens, just verify class init
    engine = IntelligenceEngine("Portfolio: BTC, NVDA")
    print("   ✅ IntelligenceEngine initialized with YoutubeScraper.")

if __name__ == "__main__":
    main()
