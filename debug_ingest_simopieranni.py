
import logging
from intelligence.engine import IntelligenceEngine

# Configure logging
logging.basicConfig(level=logging.INFO)

print("🚀 Starting Debug Ingestion for Altri Orienti...")

# Initialize Engine
engine = IntelligenceEngine(portfolio_context="Debug Portfolio")

# Force run for just this channel
# We pass source overrides to avoid running everything
video_channels = [{"handle": "@simopieranni", "filter_keyword": None, "name": "Altri Orienti"}]

print("Calling run_cycle...")
items = engine.run_cycle(sources=[], video_channels=video_channels)

print(f"Cycle finished. Returned {len(items)} items.")
for i in items:
    print(f"- {i.get('title')} ({i.get('source')})")
