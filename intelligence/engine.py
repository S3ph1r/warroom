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

    def _load_sources(self):
        """Load sources from JSON config or return defaults."""
        source_path = "data/sources.json"
        if os.path.exists(source_path):
            with open(source_path, 'r') as f:
                return json.load(f)
        return {"youtube_channels": [], "rss_feeds": []}

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
        Analyze this news/video and assign two scores (0-10) + extract relevant tags.
        CRITICAL: OUTPUT MUST BE IN ITALIAN LANGUAGE.
        
        1. RELEVANCE (Track A - Defense): 
           - How much does this DIRECTLY impact the user's specific holdings?
           - 0 = No relation. 10 = Critical impact on a held asset.
           
        2. MAGNITUDE (Track B - Discovery):
           - How significant is this event globally or for the market?
           - 0 = Noise. 10 = Historical Event / Global Disruption.

        3. TAGS:
           - Extract 2-4 keywords/hashtags (e.g. ["Crypto", "Regulation", "Bitcoin"]).

        OUTPUT FORMAT (JSON ONLY):
        {{
            "relevance_score": <int 0-10>,
            "relevance_reason": "<BREVE spiegazione in ITALIANO>",
            "magnitude_score": <int 0-10>,
            "magnitude_reason": "<BREVE spiegazione in ITALIANO>",
            "strategy": "<ALPHA|BETA|GAMMA|NOISE>",
            "tags": ["Tag1", "Tag2", "Tag3"]
        }}
        """

    def analyze_news_batch(self, news_items):
        """
        Analyzes a batch of news items using the LLM.
        Skips items that are already in memory.
        Returns list of processed items with scores.
        """
        analyzed_items = []
        items_to_process = []
        
        # 1. Filter out known items
        print(f"🧠 Checking {len(news_items)} items against memory...")
        for item in news_items:
            # Check if we already have this specific link analyzed
            if self.memory.exists(item['link']):
                # Ideally, we retrieve it from memory to show it, but for now 
                # persistence means we don't re-analyze. 
                # If we want to DISPLAY it, we should fetch it from memory.
                # However, the `run_cycle` normally returns fresh analysis.
                # To support "persistence", we should really return everything from memory + new stuff.
                # But let's stick to "don't re-analyze" for efficiency first.
                pass 
            else:
                items_to_process.append(item)
                
        print(f"   Note: {len(news_items) - len(items_to_process)} items skipped (already analyzed).")
        
        if not items_to_process:
            return []

        print(f"🧠 Analyzing {len(items_to_process)} NEW news items...")
        
        for item in items_to_process:
            prompt = self._generate_scoring_prompt(item)
            
            try:
                # We expect JSON output
                response = self.llm.chat([{"role": "user", "content": prompt}], json_mode=True)
                
                if response:
                    analysis = json.loads(response)
                    
                    item['analysis'] = analysis
                    item['relevance_score'] = analysis.get('relevance_score', 0)
                    item['magnitude_score'] = analysis.get('magnitude_score', 0)
                    item['tags'] = analysis.get('tags', [])
                    
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
        
        # Load sources from config
        config = self._load_sources()
        
        # 1. RSS Sources
        configured_rss = config.get("rss_feeds", [])
        if sources: 
            configured_rss = sources # Override if provided
            
        for url, name in configured_rss:
            try:
                items = self.rss_scraper.fetch(url, name)
                all_news.extend(items)
            except Exception as e:
                print(f"Error RSS {name}: {e}")

        # 2. YouTube Sources
        configured_channels = config.get("youtube_channels", [])
        if video_channels:
            configured_channels = video_channels # Override if provided
            
        for handle in configured_channels:
            try:
                items = self.yt_scraper.fetch_channel_updates(handle, limit=2) 
                all_news.extend(items)
            except Exception as e:
                print(f"Error YouTube {handle}: {e}")
        
        # 3. Analyze new items and store them
        new_items = self.analyze_news_batch(all_news)
        
        # 4. Return EVERYTHING from memory (last 3 days/limit 100) to the dashboard
        # This ensures we see persisted items + new items
        recent_memories = self.memory.get_recent(limit=100) 
        return [m['metadata'] for m in recent_memories] # Return formatted for dashboard
