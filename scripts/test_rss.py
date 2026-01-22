"""
Test RSS Scraper
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence.scrapers.rss_scraper import RSSScraper

def main():
    print("Testing RSS Scraper...")
    scraper = RSSScraper()
    
    # Source 1: Yahoo Finance
    url = "https://finance.yahoo.com/news/rssindex"
    print(f"\n--- 1. Yahoo Finance ({url}) ---")
    items = scraper.fetch(url, "Yahoo Finance")
    
    if items:
        print(f"✅ Success! Fetched {len(items)} items.")
        print("\nTop 3 Items:")
        for i, item in enumerate(items[:3]):
            print(f"{i+1}. [{item['published_at']}] {item['title']}")
            print(f"   Link: {item['link']}")
            print(f"   Summary: {item['summary'][:100]}...")
            print("-" * 40)
    else:
        print("❌ Failed to fetch items.")

if __name__ == "__main__":
    main()
