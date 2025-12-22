"""
RSS Scraper Module
Fetches and standardizes news from RSS feeds.
"""
import feedparser
from datetime import datetime
from email.utils import parsedate_to_datetime
import time

class RSSScraper:
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    def fetch(self, url: str, source_name: str) -> list:
        """
        Fetch RSS feed and return list of normalized news items.
        """
        print(f"Fetching {source_name} from {url}...")
        
        # feedparser handles downloads, but sometimes we might need custom headers if blocked
        # For now, standard feedparser usage
        feed = feedparser.parse(url, agent=self.user_agent)
        
        if feed.bozo:
            print(f"Warning: Feed {source_name} has parsing errors: {feed.bozo_exception}")
        
        news_items = []
        # Limit to 10 items per feed as per user requirement
        for entry in feed.entries[:10]:
            try:
                # 1. Title
                title = entry.get('title', 'No Title')
                
                # 2. Link
                link = entry.get('link', '')
                
                # 3. Date (Normalized to datetime)
                published_at = None
                if 'published_parsed' in entry:
                    # struct_time to datetime
                    published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif 'published' in entry:
                     # Attempt parsing string
                     try:
                         published_at = parsedate_to_datetime(entry.published)
                     except:
                         published_at = datetime.now()
                else:
                    published_at = datetime.now()
                
                # 4. Summary
                summary = entry.get('summary', '') or entry.get('description', '')
                
                item = {
                    'source': source_name,
                    'title': title,
                    'link': link,
                    'published_at': published_at.isoformat(),
                    'summary': summary[:500] + "..." if len(summary) > 500 else summary
                }
                news_items.append(item)
                
            except Exception as e:
                print(f"Error parsing item in {source_name}: {e}")
                continue
                
        print(f"Fetched {len(news_items)} items from {source_name}")
        return news_items

if __name__ == "__main__":
    # Quick Test
    scraper = RSSScraper()
    items = scraper.fetch("https://finance.yahoo.com/news/rssindex", "Yahoo Finance")
    for i in items[:3]:
        print(f"[{i['published_at']}] {i['title']}")
