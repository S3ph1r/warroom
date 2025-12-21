"""
Intelligence Engine
Orchestrates the analysis of news using the Dual Scoring System (Relevance + Magnitude).
"""
import json
import logging
from datetime import datetime

# Internal modules
from .llm_wrapper import LLMWrapper
from .scrapers.rss_scraper import RSSScraper
from .scrapers.youtube_scraper import YoutubeScraper
from .memory.json_memory import JsonVectorMemory

logger = logging.getLogger(__name__)

class IntelligenceEngine:
    def __init__(self, portfolio_context):
        """
        portfolio_context: str description of user portfolio (e.g. "Holdings: NVDA, AAPL...")
        """
        self.portfolio_context = portfolio_context
        self.llm = LLMWrapper(model="mistral-nemo:latest")
        self.memory = JsonVectorMemory()
        self.rss_scraper = RSSScraper()
        self.yt_scraper = YoutubeScraper()

    def _generate_scoring_prompt(self, news_item):
        return f"""
        You are a Senior Financial Intelligence Analyst.
        
        USER PORTFOLIO CONTEXT:
        {self.portfolio_context}
        
        NEWS ITEM TO ANALYZE:
        Title: {news_item['title']}
        Summary: {news_item['summary']}
        Source: {news_item.get('source')}
        Date: {news_item.get('published_at')}

        TASK:
        Analyze this news/video and assign two scores (0-10).
        CRITICAL: OUTPUT MUST BE IN ITALIAN LANGUAGE.
        
        1. RELEVANCE (Track A - Defense): 
           - How much does this DIRECTLY impact the user's specific holdings?
           - 0 = No relation. 10 = Critical impact on a held asset.
           
        2. MAGNITUDE (Track B - Discovery):
           - How significant is this event globally or for the market?
           - 0 = Noise. 10 = Historical Event / Global Disruption.

        OUTPUT FORMAT (JSON ONLY):
        {{
            "relevance_score": <int 0-10>,
            "relevance_reason": "<BREVE spiegazione in ITALIANO>",
            "magnitude_score": <int 0-10>,
            "magnitude_reason": "<BREVE spiegazione in ITALIANO>",
            "strategy": "<ALPHA|BETA|GAMMA|NOISE>"
        }}
        """

    def analyze_news_batch(self, news_items):
        """
        Analyzes a batch of news items using the LLM.
        Returns list of processed items with scores.
        """
        analyzed_items = []
        print(f"🧠 Analyzing {len(news_items)} news items...")
        
        for item in news_items:
            prompt = self._generate_scoring_prompt(item)
            
            try:
                # We expect JSON output
                response = self.llm.chat([{"role": "user", "content": prompt}], json_mode=True)
                
                if response:
                    analysis = json.loads(response)
                    
                    item['analysis'] = analysis
                    item['relevance_score'] = analysis.get('relevance_score', 0)
                    item['magnitude_score'] = analysis.get('magnitude_score', 0)
                    
                    # Store only if interesting
                    if item['relevance_score'] >= 6 or item['magnitude_score'] >= 7:
                        analyzed_items.append(item)
                        print(f"   [MATCH] R:{item['relevance_score']} M:{item['magnitude_score']} | {item['title'][:40]}...")
                    else:
                        print(f"   [Info]  R:{item['relevance_score']} M:{item['magnitude_score']} | Discarded.")
                
            except Exception as e:
                print(f"Error analyzing {item['title'][:20]}: {e}")
                continue
                
        # Bulk Memory Store for actionable items
        if analyzed_items:
            self.memory.add_news(analyzed_items)
            
        return analyzed_items

    def run_cycle(self, sources=None, video_channels=None):
        """Full cycle: Scrape (RSS + YouTube) -> Analyze -> Store"""
        all_news = []

        # 1. RSS Sources
        if not sources:
            sources = [
                ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance (General)"),
                ("https://feeds.feedburner.com/TechCrunch/", "TechCrunch (Tech Alpha)"),
                ("https://news.ycombinator.com/rss", "Hacker News (Tech Frontier)"),
                ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk (Crypto)"),
                ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World (Geopolitics)"),
                ("https://www.reddit.com/r/wallstreetbets/.rss?limit=10", "Reddit: WSB"),
            ]
            
        for url, name in sources:
            try:
                items = self.rss_scraper.fetch(url, name)
                all_news.extend(items)
            except Exception as e:
                print(f"Error RSS {name}: {e}")

        # 2. YouTube Sources
        if not video_channels:
            # Uses handles directly for the new reliable scraping method
            video_channels = [
                "@MarcoCasario",      # Italian Finance/Trading
                "@BlackBoxStocks",    # US Options/Stocks
                "@choramedia"         # Altri Orienti (Geopolitics)
            ]
            
        for handle in video_channels:
            try:
                items = self.yt_scraper.fetch_channel_updates(handle, limit=2) # Limit to 2 per channel to avoid overloading LLM
                all_news.extend(items)
            except Exception as e:
                print(f"Error YouTube {handle}: {e}")
            
        return self.analyze_news_batch(all_news)
