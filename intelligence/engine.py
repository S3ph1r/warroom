"""
Intelligence Engine
Orchestrates the analysis of news using the Dual Scoring System (Relevance + Magnitude).
"""
import json
import logging
from datetime import datetime
import os

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
           
        4. SUMMARY:
           - A concise 2-3 sentence summary in ITALIAN.

        OUTPUT FORMAT (JSON ONLY):
        {{
            "relevance_score": <int 0-10>,
            "relevance_reason": "<BREVE spiegazione in ITALIANO>",
            "magnitude_score": <int 0-10>,
            "magnitude_reason": "<BREVE spiegazione in ITALIANO>",
            "strategy": "<ALPHA|BETA|GAMMA|NOISE>",
            "tags": ["Tag1", "Tag2", "Tag3"],
            "relevance_score": <int 0-10>,
            "relevance_reason": "<BREVE spiegazione in ITALIANO>",
            "magnitude_score": <int 0-10>,
            "magnitude_reason": "<BREVE spiegazione in ITALIANO>",
            "strategy": "<ALPHA|BETA|GAMMA|NOISE>",
            "tags": ["Tag1", "Tag2", "Tag3"],
            "summary": "<Concise summary in Italian>",
            "translated_title": "<Title translated to Italian>"
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
                    
                    # USE AI SUMMARY and TITLE if available
                    if analysis.get('translated_title'):
                        item['title'] = analysis.get('translated_title')
                        
                    if analysis.get('summary'):
                        item['summary'] = analysis.get('summary')
                    
                    # ALWAYS Store analyzed items (Feed-First approach)
                    # We still compute scores for filtering later, but we capture everything now.
                    item['analysis'] = analysis # Ensure analysis is attached
                    
                    # Incremental Save
                    self.memory.add_news([item])
                    analyzed_items.append(item)
                    print(f"   [SAVED] R:{item['relevance_score']} M:{item['magnitude_score']} | {item['title'][:40]}...")
                
            except Exception as e:
                print(f"Error analyzing {item['title'][:20]}: {e}")
                continue
                
        # Bulk Memory Store (redundant if incremental, but safe)
        if analyzed_items:
            # self.memory.add_news(analyzed_items) # Already saved incrementally
            pass
            
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
            # Normalize override: support both list of strings and list of dicts
            normalized = []
            for item in video_channels:
                if isinstance(item, str):
                    normalized.append({"handle": item, "filter_keyword": None})
                else:
                    normalized.append(item)
            configured_channels = normalized
            
        for ch_config in configured_channels:
            # Handle both old string format (legacy safety) and new object format
            if isinstance(ch_config, str):
                handle = ch_config
                keyword = None
                display_name = None
            else:
                handle = ch_config.get("handle")
                keyword = ch_config.get("filter_keyword")
                display_name = ch_config.get("name")
                
            try:
                # We need to fetch 5 items, but ONLY process them if not in memory.
                # The scraper fetches metadata first, allowing us to filter before "get_transcript" 
                # effectively SAVING QUOTA/TIME. 
                # HOWEVER, `youtube_scraper` currently combines fetch+transcript.
                # Optimization: We let it fetch, but since it returns quickly for 5 items, it's okay.
                # Future: Split `get_videos` and `get_transcript` in engine.
                
                # Optimization: Check if we have ANY items from this handle in memory to decide fetch depth
                # Check against display_name OR fallback format
                target_source_name = display_name if display_name else f"YouTube ({handle})"
                has_history = any(m['metadata'].get('source') == target_source_name for m in self.memory.data)
                
                fetch_limit = 5 if has_history else 1
                
                items = self.yt_scraper.fetch_channel_updates(handle, limit=fetch_limit, filter_keyword=keyword, display_name=display_name) 
                
                # Filter out items already in memory BEFORE analyzing
                fresh_items = []
                for item in items:
                    if not self.memory.exists(item['link']):
                        fresh_items.append(item)
                    else:
                        print(f"   [Cache Hit] Video already analyzed: {item['title'][:30]}...")
                        
                all_news.extend(fresh_items)
            except Exception as e:
                print(f"Error YouTube {handle}: {e}")
        
        # 3. Analyze new items and store them
        new_items = self.analyze_news_batch(all_news)
        
        # 4. Return EVERYTHING from memory (last 3 days/limit 100) to the dashboard
        # This ensures we see persisted items + new items
        recent_memories = self.memory.get_recent(limit=100) 
        return [m['metadata'] for m in recent_memories] # Return formatted for dashboard
