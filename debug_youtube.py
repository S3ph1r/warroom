
from intelligence.scrapers.youtube_scraper import YoutubeScraper
from datetime import datetime
import json

def test_scraper():
    scraper = YoutubeScraper()
    
    # Test 1: Marco Casario
    print("\n--- Testing @MarcoCasario ---")
    videos = scraper.fetch_channel_updates("@MarcoCasario", limit=3)
    for v in videos:
        print(f"Title: {v['title']}")
        print(f"Date: {v['published_at']}")
        print(f"Link: {v['link']}")
        print("-" * 20)
        
    # Test 2: Chora Media (Filtered)
    print("\n--- Testing @choramedia [BlackBox] ---")
    videos_bb = scraper.fetch_channel_updates("@choramedia", limit=5, filter_keyword="BlackBox")
    for v in videos_bb:
        print(f"Title: {v['title']}")
        print(f"Date: {v['published_at']}")
        print("-" * 20)

if __name__ == "__main__":
    test_scraper()
