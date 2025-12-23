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

import logging
from collections import deque

# --- LOGGING SETUP ---
log_buffer = deque(maxlen=100)  # Keep last 100 logs

class BufferHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Add simple timestamp if not present
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {msg}"
            log_buffer.append(log_entry)
        except Exception:
            self.handleError(record)

# Configure Root Logger to use our Buffer
buffer_handler = BufferHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
buffer_handler.setFormatter(formatter)
logging.getLogger().addHandler(buffer_handler)
logging.getLogger().setLevel(logging.INFO)

# Also capture 'intelligence' specifically if needed, but root covers it.

app = FastAPI(title="War Room API")

# CORS for Svelte Dev Server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/logs")
def get_logs():
    return {"logs": list(log_buffer)}

@app.delete("/api/logs")
def clear_logs():
    log_buffer.clear()
    return {"status": "cleared"}

from scripts.inspect_source import audit_channel_strategy

# Models
class SourceUpdate(BaseModel):
    handle: Optional[str] = None
    url: Optional[str] = None

@app.post("/api/sources")
def add_source(source: SourceUpdate):
    source_path = PROJECT_ROOT / "data" / "sources.json"
    if source_path.exists():
        with open(source_path, 'r') as f:
            data = json.load(f)
    else:
        data = {"youtube_channels": []}
        
    new_entry = None
    
    # CASE 1: Full Discovery via URL
    if source.url:
        logger.info(f"Running discovery for: {source.url}")
        new_entry = audit_channel_strategy(source.url)
        if not new_entry:
            raise HTTPException(status_code=400, detail="Could not discover channel from URL. Is it valid?")
            
    # CASE 2: Manual Handle (Legacy)
    elif source.handle:
        new_entry = {
            "handle": source.handle,
            "name": source.handle,
            "strategy": "STRATEGY_HYBRID",
            "filter_keyword": None
        }
    else:
         raise HTTPException(status_code=400, detail="Must provide 'url' or 'handle'")

    # Check for duplicates (by handle)
    # Filter out existing with same handle
    existing_handles = []
    normalized_list = []
    
    for item in data.get("youtube_channels", []):
        if isinstance(item, str):
            normalized_list.append({"handle": item, "name": item, "strategy": "STRATEGY_HYBRID"})
            existing_handles.append(item)
        else:
            normalized_list.append(item)
            existing_handles.append(item.get("handle"))
            
    if new_entry['handle'] in existing_handles:
        # Update existing
        logger.info(f"Updating existing source: {new_entry['handle']}")
        final_list = []
        for item in normalized_list:
            if item['handle'] == new_entry['handle']:
                final_list.append(new_entry) # Replace with new discovery
            else:
                final_list.append(item)
        data["youtube_channels"] = final_list
    else:
        # Add new
        logger.info(f"Adding new source: {new_entry['handle']}")
        data.setdefault("youtube_channels", [])
        # We need to ensure we don't break the mix of strings/dicts if any strings left, 
        # but better to normalize all if we can. 
        # For safety, just append.
        # But wait, we reconstructed 'normalized_list' above but didn't assign it back to data if no dupes?
        # Let's fix.
        if isinstance(data["youtube_channels"], list):
             # Just append object. Engine handles mixed types.
             data["youtube_channels"].append(new_entry)

    with open(source_path, 'w') as f:
        json.dump(data, f, indent=2)
            
    return data

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
    total_day_pl = 0

    for h in holdings:
        hid = h["id"]
        ld = live_data.get(hid, {})

        # Merge live data into holding
        h_data = {
            **h,
            "quantity": float(h.get("quantity", 0) or 0),
            "live_price": ld.get("live_price") or h.get("current_price") or 0,
            "current_value": ld.get("live_value") or h.get("current_value") or 0,
            "pnl": ld.get("pnl") or 0,
            "pnl_pct": ld.get("pnl_pct") or 0,
            "day_pl": ld.get("day_pl") or 0,
            "day_change_pct": ld.get("day_change_pct") or 0,
            "source": ld.get("source", "DB"),
        }
        processed_holdings.append(h_data)
        total_day_pl += h_data["day_pl"]

        # Aggregation
        broker = h["broker"]
        if broker not in broker_totals:
            broker_totals[broker] = {"value": 0, "cost": 0, "day_pl": 0}

        broker_totals[broker]["value"] += h_data["current_value"]
        broker_totals[broker]["day_pl"] += h_data["day_pl"]

        # Use pre-calculated cost basis from service (handles FX)
        cost = ld.get("cost_basis", 0)
        if cost == 0 and h["quantity"] and h["purchase_price"]:
            cost = h["quantity"] * h["purchase_price"]

        broker_totals[broker]["cost"] += cost

    total_value = sum(b["value"] for b in broker_totals.values())
    total_cost = sum(b["cost"] for b in broker_totals.values())
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    total_day_change_pct = (
        (total_day_pl / (total_value - total_day_pl) * 100)
        if (total_value - total_day_pl) > 0
        else 0
    )

    # Post-process Broker Totals for Percentages
    for bname, bstats in broker_totals.items():
        bstats["pnl"] = bstats["value"] - bstats["cost"]
        bstats["pnl_pct"] = (
            (bstats["pnl"] / bstats["cost"] * 100) if bstats["cost"] > 0 else 0
        )
        prev_value = bstats["value"] - bstats["day_pl"]
        bstats["day_change_pct"] = (
            (bstats["day_pl"] / prev_value * 100) if prev_value > 0 else 0
        )

    # Asset Allocation
    asset_totals = {}
    for h in processed_holdings:
        atype = h.get("asset_type", "Unknown")
        if atype not in asset_totals:
            asset_totals[atype] = 0
        asset_totals[atype] += h["current_value"]

    data = {
        "holdings": processed_holdings,
        "broker_totals": broker_totals,
        "asset_totals": asset_totals,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "total_day_pl": total_day_pl,
        "total_day_change_pct": total_day_change_pct,
        "count": len(holdings),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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



@app.delete("/api/sources")
def delete_source(handle: str):
    logger.info(f"🗑️ Request to delete source: '{handle}'")
    source_path = PROJECT_ROOT / "data" / "sources.json"
    if source_path.exists():
        with open(source_path, 'r') as f:
            data = json.load(f)
            
        original_len = len(data.get("youtube_channels", []))
        
        # Filter out the handle
        new_list = []
        for item in data.get("youtube_channels", []):
            item_handle = item if isinstance(item, str) else item.get("handle")
            # Debug log for comparison
            # logger.info(f"   Comparing '{item_handle}' vs '{handle}'")
            if item_handle != handle:
                new_list.append(item)
                
        if len(new_list) < original_len:
            data["youtube_channels"] = new_list
            with open(source_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"✅ Deleted {handle}")
            return {"status": "deleted", "handle": handle}
        else:
            logger.warning(f"❌ Handle '{handle}' not found in sources.")
            
    raise HTTPException(status_code=404, detail="Source not found")

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
