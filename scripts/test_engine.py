"""
Integration Test: Intelligence Engine (The Brain)
"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence.engine import IntelligenceEngine

def main():
    print("--- 🧠 Intelligence Engine Test ---")
    
    # 1. Define Context (The "Portfolio")
    context = """
    User Profile:
    - Risk Tolerance: Medium/High
    - Portfolio Top Holdings: 
      - NVIDIA (NVDA) [High Exposure]
      - Bitcoin (BTC) [Medium Exposure]
      - Apple (AAPL)
      - US Treasury Bonds (TLT)
    - Watchlist:
      - Artificial Intelligence
      - Energy / Oil
      - Geopolitics (China/Taiwan)
    """
    
    print("\n1. Initializing Engine with Context:")
    print(context.strip())
    
    engine = IntelligenceEngine(portfolio_context=context)
    
    # 2. Run Cycle (Fetch + Analyze)
    # We limit to Yahoo Finance for this test
    print("\n2. Running Intelligence Cycle (Live)...")
    start_time = time.time()
    
    # Using a limited fetch for testing speed (default fetches all)
    # For test we cheat and use internal method to get just a few items first
    
    # Fetch Phase
    print("   Fetching news...")
    from intelligence.scrapers.rss_scraper import RSSScraper
    scraper = RSSScraper()
    items = scraper.fetch("https://finance.yahoo.com/news/rssindex", "Yahoo Finance Test")
    
    if not items:
        print("❌ No news fetched.")
        return

    # Take first 3 items
    test_batch = items[:3]
    print(f"   Analyzing {len(test_batch)} items...")
    
    # Analyze Phase
    analyzed_items = engine.analyze_news_batch(test_batch)
    
    duration = time.time() - start_time
    print(f"\n✅ Cycle Complete in {duration:.2f}s")
    
    # 3. Report Results
    print("\n--- 📊 ANALYSIS REPORT ---")
    if not analyzed_items:
        print("No 'Actionable' items found (Relevance < 6 and Magnitude < 7).")
        print("This means the filter is working (blocking noise).")
    else:
        for item in analyzed_items:
            scores = item.get('analysis', {})
            print(f"\n📰 {item['title']}")
            print(f"   🎯 Relevance: {scores.get('relevance_score')}/10 (Track A)")
            print(f"      Reason: {scores.get('relevance_reason')}")
            print(f"   🌍 Magnitude: {scores.get('magnitude_score')}/10 (Track B)")
            print(f"      Reason: {scores.get('magnitude_reason')}")
            print(f"   ♟️ Strategy: {scores.get('strategy')}")

if __name__ == "__main__":
    main()
