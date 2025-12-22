import sys
from pathlib import Path
import json
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.portfolio_service import get_all_holdings
from services.price_service_v5 import get_live_values_for_holdings, clear_cache
from intelligence.engine import IntelligenceEngine
from intelligence.engine import IntelligenceEngine
from intelligence.memory.json_memory import JsonVectorMemory
from services.council import council # Singleton instance

app = FastAPI(title="War Room API")

# CORS for Svelte Dev Server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class SourceUpdate(BaseModel):
    handle: str

class IntelligenceScanRequest(BaseModel):
    force: bool = False

class CouncilRequest(BaseModel):
    query: Optional[str] = None

# --- PERSISTENCE HELPERS ---
PORTFOLIO_SNAPSHOT = PROJECT_ROOT / "data" / "portfolio_snapshot.json"
INTELLIGENCE_SNAPSHOT = PROJECT_ROOT / "data" / "intelligence_snapshot.json"

def _save_snapshot(path: Path, data: dict):
    with open(path, 'w') as f:
        json.dump(data, f)

def _load_snapshot(path: Path):
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return None

def build_portfolio_data():
    """Calculate complete portfolio data (heavy operation)."""
    holdings = get_all_holdings()
    if not holdings:
        return {"holdings": [], "totals": {}, "total_value": 0}
        
    live_data = get_live_values_for_holdings(holdings)
    
    # Calculate Totals
    broker_totals = {}
    processed_holdings = []
    
    for h in holdings:
        hid = h['id']
        ld = live_data.get(hid, {})
        
        # Merge live data into holding
        h_data = {
            **h,
            "live_price": ld.get('live_price', h.get('current_price')),
            "current_value": ld.get('live_value', h.get('current_value')),
            "pnl": ld.get('pnl', 0),
            "pnl_pct": ld.get('pnl_pct', 0),
            "source": ld.get('source', 'DB')
        }
        processed_holdings.append(h_data)
        
        # Aggregation
        broker = h['broker']
        if broker not in broker_totals:
            broker_totals[broker] = {"value": 0, "cost": 0}
        
        broker_totals[broker]["value"] += h_data["current_value"]
        
        # Use pre-calculated cost basis from service (handles FX)
        cost = ld.get('cost_basis', 0)
        if cost == 0 and h['quantity'] and h['purchase_price']:
                cost = h['quantity'] * h['purchase_price']
        
        broker_totals[broker]["cost"] += cost

    total_value = sum(b['value'] for b in broker_totals.values())
    total_cost = sum(b['cost'] for b in broker_totals.values())
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # Asset Allocation
    asset_totals = {}
    for h in processed_holdings:
        atype = h.get('asset_type', 'Unknown')
        if atype not in asset_totals:
            asset_totals[atype] = 0
        asset_totals[atype] += h['current_value']
    
    data = {
        "holdings": processed_holdings,
        "broker_totals": broker_totals,
        "asset_totals": asset_totals,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "count": len(holdings),
        "last_updated": "Just now"
    }
    _save_snapshot(PORTFOLIO_SNAPSHOT, data)
    return data

from datetime import datetime, timedelta

def build_intelligence_data():
    """Build intelligence data (heavy operation). Optimized for frontend."""
    memory = JsonVectorMemory()
    all_items = memory.data
    
    # Configuration
    DAYS_LOOKBACK = 700 # Extended to capture very old content (2024 vs 2025)
    MAX_PER_SOURCE = 10
    
    # Filter for last N days
    cutoff = datetime.now() - timedelta(days=DAYS_LOOKBACK)
    recent_items = []
    
    for item in all_items:
        try:
            pub_date_str = item['metadata'].get('published_at') or item.get('created_at')
            if pub_date_str:
                if 'Z' in pub_date_str:
                     pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                else:
                     pub_date = datetime.fromisoformat(pub_date_str)

                if pub_date.replace(tzinfo=None) > cutoff.replace(tzinfo=None):
                    # Attach parsed date object for sorting (removed before JSON)
                    item['metadata']['_parsed_date'] = pub_date
                    recent_items.append(item['metadata'])
        except Exception:
            continue
            
    # Group by Source
    grouped = {}
    for item in recent_items:
        source = item.get('source', 'Unknown')
        if source not in grouped:
            grouped[source] = []
        grouped[source].append(item)
        
    # Sort and Slice per Source
    final_items = []
    for source, items in grouped.items():
        # Sort by date descending
        items.sort(key=lambda x: x.get('_parsed_date', datetime.min), reverse=True)
        
        # Take top N
        top_items = items[:MAX_PER_SOURCE]
        
        # Clean up temporary key
        for i in top_items:
            if '_parsed_date' in i:
                del i['_parsed_date']
                
        final_items.extend(top_items)
    
    # Global Sort for Frontend (Mix sources chronologically)
    # Re-parsing is expensive, but for <50 items it's fine. 
    # Or we could have kept the list before flattening.
    # Actually, let's just sort by published_at string which works well for ISO
    final_items.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    
    _save_snapshot(INTELLIGENCE_SNAPSHOT, final_items)
    return final_items

# --- PORTFOLIO ENDPOINTS ---

@app.get("/api/portfolio")
def get_portfolio():
    try:
        # Try to load instantaneous snapshot
        data = _load_snapshot(PORTFOLIO_SNAPSHOT)
        if data:
            return data
        # Fallback to build
        return build_portfolio_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
def refresh_data():
    try:
        clear_cache()
        # Rebuild snapshots
        p_data = build_portfolio_data()
        i_data = build_intelligence_data()
        return {"status": "Refreshed", "portfolio_count": p_data['count']}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

# --- INTELLIGENCE ENDPOINTS ---

# Logging setup
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
import os

@app.get("/api/intelligence")
def get_intelligence():
    try:
        # data = _load_snapshot(INTELLIGENCE_SNAPSHOT)
        # Debugging: Always try load, log result
        data = _load_snapshot(INTELLIGENCE_SNAPSHOT)
        if data:
             return data
        return build_intelligence_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligence/scan")
def run_scan(request: IntelligenceScanRequest):
    try:
        # Construct context
        holdings = get_all_holdings()
        tickers = ", ".join([h.get('ticker', '') for h in holdings[:15]])
        context = f"Portfolio: {tickers}"
        
        engine = IntelligenceEngine(portfolio_context=context)
        new_items = engine.run_cycle()
        
        # Rebuild snapshot to include new items
        build_intelligence_data()
        
        return {"new_items": len(new_items), "items": new_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- SETTINGS ENDPOINTS ---

@app.get("/api/sources")
def get_sources():
    source_path = PROJECT_ROOT / "data" / "sources.json"
    if source_path.exists():
        with open(source_path, 'r') as f:
            return json.load(f)
    return {"youtube_channels": []}

@app.post("/api/sources")
def add_source(source: SourceUpdate):
    source_path = PROJECT_ROOT / "data" / "sources.json"
    if source_path.exists():
        with open(source_path, 'r') as f:
            data = json.load(f)
    else:
        data = {"youtube_channels": []}
        
    if source.handle not in data["youtube_channels"]:
        data["youtube_channels"].append(source.handle)
        with open(source_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    return data

@app.get("/api/status")
def health_check():
    return {"status": "online", "version": "0.5.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8201, reload=True)

from pydantic import BaseModel
from typing import Optional

class CouncilRequest(BaseModel):
    query: Optional[str] = None
    force_refresh: bool = False

@app.post("/api/council/consult")
async def consult_council(request: CouncilRequest):
    """
    Triggers a strategic consultation with The Council (Gemini + Claude + DeepSeek + Qwen).
    """
    try:
        result = await council.convene_council(user_query=request.query, force_refresh=request.force_refresh)
        return result
    except Exception as e:
        logger.error(f"Council Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RefreshItemRequest(BaseModel):
    item_id: str

@app.post("/api/council/refresh-item")
async def refresh_council_item(request: RefreshItemRequest):
    try:
        updated_item = await council.refresh_council_item(request.item_id)
        return updated_item
    except Exception as e:
        logger.error(f"Refresh Item Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
