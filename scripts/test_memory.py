"""
Integration Test: Scraper -> Embed -> Vector DB
"""
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence.scrapers.rss_scraper import RSSScraper
from intelligence.memory.chroma_client import VectorMemory

def main():
    print("--- 🧠 Memeory System Integration Test ---")
    
    # 1. Init Memory (Connects to Chroma + Ollama)
    print("\n1. Initializing Vector Memory...")
    memory = VectorMemory(embedding_model="mistral-nemo:latest")
    
    if not memory._check_connection():
        print("❌ Connection failed. Ensure Docker is running.")
        return

    # 2. Fetch News (Real Data)
    print("\n2. Fetching recent news...")
    scraper = RSSScraper()
    news = scraper.fetch("https://finance.yahoo.com/news/rssindex", "Yahoo Finance Integration Test")
    
    if not news:
        print("❌ No news fetched.")
        return
        
    # Take only 3 items for speed test
    sample_news = news[:3]
    
    # 3. Embed & Store
    print(f"\n3. Embedding & Storing {len(sample_news)} items...")
    start_time = time.time()
    count = memory.add_news(sample_news)
    duration = time.time() - start_time
    print(f"   Done in {duration:.2f}s")
    
    if count == 0:
        print("❌ Failed to store items.")
        return

    # 4. Semantic Search
    print("\n4. Testing Semantic Search...")
    query = "market trends"
    print(f"   Query: '{query}'")
    results = memory.query_similar(query, n_results=1)
    
    if results and 'documents' in results and results['documents']:
        doc = results['documents'][0][0]
        meta = results['metadatas'][0][0]
        print(f"   ✅ Match Found: {meta['title']}")
        print(f"   📄 Excerpt: {doc[:100]}...")
    else:
        print("❌ Search returned no results.")

if __name__ == "__main__":
    main()
