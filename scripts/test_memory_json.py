"""
Integration Test: Scraper -> JSON Vector Memory
"""
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the NEW JsonVectorMemory
from intelligence.memory.json_memory import JsonVectorMemory
from intelligence.scrapers.rss_scraper import RSSScraper

def main():
    print("--- 🧠 JSON Memory System Integration Test ---")
    
    # 1. Init Memory
    print("\n1. Initializing Memory (File-based)...")
    memory = JsonVectorMemory(embedding_model="mistral-nemo:latest")
    
    # 2. Fetch News (Real Data)
    print("\n2. Fetching recent news...")
    scraper = RSSScraper()
    news = scraper.fetch("https://finance.yahoo.com/news/rssindex", "Yahoo Finance Test")
    
    if not news:
        print("❌ No news fetched.")
        return
        
    # Take 5 items for test
    sample_news = news[:5]
    
    # 3. Embed & Store
    print(f"\n3. Embedding & Storing {len(sample_news)} items...")
    start_time = time.time()
    count = memory.add_news(sample_news)
    duration = time.time() - start_time
    print(f"   Done in {duration:.2f}s")

    # 4. Spatial/Semantic Search
    # We ask a question that requires "understanding", not just keywords.
    queries = ["market crash", "tech innovation", "earnings report"]
    
    print("\n4. Testing Spatial Search...")
    for q in queries:
        print(f"\n🔎 Query: '{q}'")
        results = memory.search(q, n_results=1)
        if results:
            best = results[0]
            print(f"   ✅ Best Match (Score: {best['score']})")
            print(f"   📰 Title: {best['metadata']['title']}")
            print(f"   📄 Summary: {best['metadata']['summary'][:100]}...")
        else:
            print("   (No match found)")

if __name__ == "__main__":
    main()
