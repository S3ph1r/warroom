"""
Test Candidate RSS Sources
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence.scrapers.rss_scraper import RSSScraper

def main():
    scraper = RSSScraper()
    
    candidates = [
        ("Tech (Alpha)", "https://feeds.feedburner.com/TechCrunch/"),
        ("Hacker News (Alpha)", "https://news.ycombinator.com/rss"),
        ("Crypto (Beta)", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        # Reuters is often tricky with RSS, using a reliable aggregator or alternative if fails
        ("GeoPol (Gamma)", "http://feeds.bbci.co.uk/news/world/rss.xml"), 
        ("Macro (Economics)", "https://www.investing.com/rss/news_14.rss"),
        ("Reddit: WSB (Retail Alpha)", "https://www.reddit.com/r/wallstreetbets/.rss?limit=10"),
        ("Reddit: Economics", "https://www.reddit.com/r/economics/.rss?limit=10"),
        ("Twitter (via Nitter): Elon Musk", "https://nitter.net/elonmusk/rss"),  # Often unstable
        ("Twitter (via Nitter): OpenBB", "https://nitter.net/openbb_finance/rss") # Testing tech connection
    ]

    print("--- Testing Sources ---")
    for category, url in candidates:
        print(f"\n📡 Testing {category}...")
        try:
            items = scraper.fetch(url, category)
            if items:
                print(f"   ✅ OK! Got {len(items)} items.")
                print(f"   Sample: {items[0]['title']}")
            else:
                print("   ❌ Failed (Empty).")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    main()
