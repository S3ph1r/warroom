"""
🎯 WAR ROOM - Dashboard v4
Clean architecture using price_service_v5

Data Flow:
- DB: ticker, isin, quantity, broker, purchase_price, currency
- API: live_price from Yahoo/CoinGecko
- Calc: live_value = qty × live_price, P/L = live_value - cost_basis
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

import html  # For escaping user content in tiles

# Page config
st.set_page_config(
    page_title="War Room",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Modern Tech Dark Mode
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>
    /* Global Dark Theme */
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #0d0d12 100%);
    }
    
    /* Typography - Tech Publication Style */
    html, body, [class*="st-"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main Header - Bold Tech Branding */
    .main-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 50%, #ff006e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    
    /* Metrics Cards - Deep Dark */
    .stMetric > div {
        background: rgba(13, 13, 18, 0.95);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255,255,255,0.08);
        backdrop-filter: blur(10px);
    }
    .stMetric label {
        color: #6b7280 !important;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #f9fafb !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }
    
    /* Intelligence Tiles - Premium Dark Cards */
    .news-tile {
        background: rgba(13, 13, 18, 0.98);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(255,255,255,0.06);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        min-height: 160px;
    }
    .news-tile:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 212, 255, 0.3);
        box-shadow: 0 4px 24px rgba(0, 212, 255, 0.1);
    }
    
    /* Strategy Accent Borders */
    .news-tile.alpha { border-left: 3px solid #10b981; }  /* Emerald */
    .news-tile.beta { border-left: 3px solid #3b82f6; }   /* Blue */
    .news-tile.gamma { border-left: 3px solid #ef4444; }  /* Red */
    .news-tile.noise { border-left: 3px solid #374151; }  /* Gray */
    
    /* Tile Typography */
    .tile-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: #f3f4f6;
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }
    .tile-title a { 
        color: inherit; 
        text-decoration: none;
        transition: color 0.2s;
    }
    .tile-title a:hover { color: #00d4ff; }
    
    .tile-meta {
        font-size: 0.7rem;
        color: #6b7280;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    
    /* Score Badges - Compact Pills */
    .score-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 6px;
        font-family: 'Space Grotesk', monospace;
    }
    .score-badge.relevance { 
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .score-badge.magnitude { 
        background: rgba(236, 72, 153, 0.2);
        color: #f472b6;
        border: 1px solid rgba(236, 72, 153, 0.3);
    }
    
    .tile-reason {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.75rem;
        line-height: 1.5;
    }
    
    /* Video Badge - YouTube Red */
    .video-badge {
        background: #dc2626;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        margin-left: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #9ca3af;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0, 212, 255, 0.1) !important;
        color: #00d4ff !important;
    }
    
    /* Dividers */
    hr {
        border-color: rgba(255,255,255,0.06);
    }
    
    /* Multiselect Styling */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(59, 130, 246, 0.2);
        border-color: rgba(59, 130, 246, 0.3);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(ttl=60)
def load_holdings():
    """Load holdings from DB."""
    try:
        from services.portfolio_service import get_all_holdings
        return get_all_holdings()
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []


def fetch_live_prices(holdings: list, use_cache: bool = True):
    """Fetch live prices using price_service_v5 with OpenFIGI."""
    try:
        from services.price_service_v5 import get_live_values_for_holdings, clear_cache
        if not use_cache:
            clear_cache()
        return get_live_values_for_holdings(holdings)
    except Exception as e:
        st.error(f"Price Error: {e}")
        return {}


def calculate_broker_totals(holdings: list, live_data: dict) -> dict:
    """Calculate totals per broker using live values."""
    totals = {}
    for h in holdings:
        broker = h['broker']
        hid = h['id']
        
        if hid in live_data:
            value = live_data[hid]['live_value']
            cost = live_data[hid]['cost_basis']
        else:
            value = h['current_value']
            cost = value
        
        if broker not in totals:
            totals[broker] = {'value': 0, 'cost': 0}
        
        totals[broker]['value'] += value
        totals[broker]['cost'] += cost
    
    # Calculate P/L
    for broker in totals:
        v = totals[broker]['value']
        c = totals[broker]['cost']
        totals[broker]['pnl'] = v - c
        totals[broker]['pnl_pct'] = ((v - c) / c * 100) if c > 0 else 0
    
    return totals


# ============================================================
# MAIN
# ============================================================

def main():
    # Header
    st.markdown('<p class="main-header">🎯 THE WAR ROOM</p>', unsafe_allow_html=True)
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        use_live = st.toggle("💹 Live Prices", value=True)
        
        if st.button("🔄 Refresh All"):
            st.cache_data.clear()
            from services.price_service_v5 import clear_cache
            clear_cache()
            st.rerun()
    
    # Tabs
    tab_portfolio, tab_intelligence = st.tabs(["💰 Portfolio", "🧠 Intelligence"])

    with tab_portfolio:
        # Load data
        with st.spinner("Loading holdings..."):
            holdings = load_holdings()
        
        if not holdings:
            st.error("No holdings found. Run ingestion first.")
            return
        
        # Fetch prices
        live_data = {}
        if use_live:
            with st.spinner("Fetching live prices..."):
                live_data = fetch_live_prices(holdings, use_cache=True)
        
        # Calculate broker totals
        broker_totals = calculate_broker_totals(holdings, live_data)
        
        # Portfolio total
        total_value = sum(b['value'] for b in broker_totals.values())
        total_cost = sum(b['cost'] for b in broker_totals.values())
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        st.divider()
        
        # ==================== KPI CARDS ====================
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Portfolio Value",
                f"€{total_value:,.2f}",
                delta=f"€{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)" if use_live else None
            )
        
        with col2:
            pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
            st.metric(f"{pnl_icon} Total P/L", f"€{total_pnl:,.2f}" if use_live else "N/A")
        
        with col3:
            st.metric("📈 Holdings", f"{len(holdings)}")
        
        with col4:
            st.metric("🏦 Brokers", f"{len(broker_totals)}")
        
        st.divider()
        
        # ==================== BROKER BREAKDOWN ====================
        st.subheader("🏦 Portfolio by Broker")
        
        sorted_brokers = sorted(broker_totals.items(), key=lambda x: x[1]['value'], reverse=True)
        cols = st.columns(len(sorted_brokers))
        
        for i, (broker, data) in enumerate(sorted_brokers):
            with cols[i]:
                pct = (data['value'] / total_value * 100) if total_value > 0 else 0
                st.metric(
                    broker.replace("_", " "),
                    f"€{data['value']:,.2f}",
                    delta=f"{pct:.1f}%"
                )
        
        st.divider()
        
        # ==================== CHARTS ====================
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("🎯 Allocation by Broker")
            broker_df = pd.DataFrame([
                {"Broker": k.replace("_", " "), "Value": v['value']}
                for k, v in broker_totals.items()
            ])
            fig = px.pie(broker_df, values='Value', names='Broker', hole=0.4)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            st.subheader("📊 Allocation by Type")
            # Calculate by asset type
            type_totals = {}
            for h in holdings:
                atype = h.get('asset_type', 'Other')
                hid = h['id']
                val = live_data[hid]['live_value'] if hid in live_data else h['current_value']
                type_totals[atype] = type_totals.get(atype, 0) + val
            
            type_df = pd.DataFrame([
                {"Type": k, "Value": v}
                for k, v in type_totals.items()
            ])
            fig = px.pie(type_df, values='Value', names='Type', hole=0.4)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # ==================== HOLDINGS TABLE ====================
        st.subheader("📋 Holdings Details")
        
        # Filters
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            broker_filter = st.selectbox("Filter Broker", ["All"] + list(broker_totals.keys()))
        with col_f2:
            type_filter = st.selectbox("Filter Type", ["All"] + list(type_totals.keys()))
        
        # Build table
        table_rows = []
        for h in holdings:
            broker = h['broker']
            atype = h.get('asset_type', '')
            
            if broker_filter != "All" and broker != broker_filter:
                continue
            if type_filter != "All" and atype != type_filter:
                continue
            
            hid = h['id']
            qty = h['quantity']
            purch_price = h.get('purchase_price') or h.get('current_price') or 0
            
            if hid in live_data:
                ld = live_data[hid]
                live_price = ld['live_price']
                live_value = ld['live_value']
                pnl = ld['pnl']
                pnl_pct = ld['pnl_pct']
                source = ld['source']
            else:
                live_price = purch_price
                live_value = qty * purch_price
                pnl = 0
                pnl_pct = 0
                source = "DB"
            
            table_rows.append({
                'Broker': broker.replace('_', ' '),
                'Ticker': h.get('ticker', ''),
                'ISIN': h.get('isin', '') or '',
                'Qty': qty,
                'Live Price': live_price,
                'Purch. Price': purch_price,
                'Value': live_value,
                'P/L': pnl,
                'P/L %': pnl_pct,
                'Source': source,
            })
        
        if table_rows:
            df = pd.DataFrame(table_rows)
            df = df.sort_values('Value', ascending=False)
            
            st.dataframe(
                df.style.format({
                    'Qty': '{:.4f}',
                    'Live Price': '€{:.2f}',
                    'Purch. Price': '€{:.2f}',
                    'Value': '€{:,.2f}',
                    'P/L': '€{:,.2f}',
                    'P/L %': '{:.1f}%'
                }).applymap(
                    lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 
                             ('color: red' if isinstance(x, (int, float)) and x < 0 else ''),
                    subset=['P/L', 'P/L %']
                ),
                use_container_width=True,
                height=500
            )
            
            # Summary
            total_shown = sum(r['Value'] for r in table_rows)
            total_pnl_shown = sum(r['P/L'] for r in table_rows)
            st.info(f"**Shown:** €{total_shown:,.2f} | **P/L:** €{total_pnl_shown:,.2f}")

    # ==================== INTELLIGENCE TAB ====================
    with tab_intelligence:
        st.markdown("### 🧠 The Filter (Intelligence Engine)")
        col_act1, col_act2 = st.columns([1, 4])
        
        with col_act1:
            if st.button("🔄 Scan & Analyze", type="primary"):
                with st.spinner("🤖 Reading news & scanning videos... (This takes ~30s)"):
                    try:
                        from intelligence.engine import IntelligenceEngine
                        # Minimal context for now (can be expanded to real portfolio dump)
                        ctx = "Portfolio: " + ", ".join([h.get('ticker', '') for h in holdings[:10]])
                        engine = IntelligenceEngine(portfolio_context=ctx)
                        new_items = engine.run_cycle()
                        st.success(f"Analizzati {len(new_items)} nuovi elementi!")
                    except Exception as e:
                        st.error(f"Analysis Failed: {e}")

        # Load Memory
        from intelligence.memory.json_memory import JsonVectorMemory
        memory = JsonVectorMemory()
        memories = memory.data
        
        if not memories:
            st.info("Nessuna news in memoria. Clicca 'Scan & Analyze'.")
        else:
            # 1. Filters
            all_sources = sorted(list(set([m['metadata'].get('source', 'Unknown') for m in memories])))
            selected_sources = st.multiselect("Filtra per Fonte", all_sources, default=all_sources)
            
            # Filter Logic
            filtered_memories = [m for m in memories if m['metadata'].get('source', 'Unknown') in selected_sources]
            
            # Sorting: Priority = Relevance + Magnitude
            filtered_memories.sort(
                key=lambda x: (x['metadata'].get('relevance_score', 0) + x['metadata'].get('magnitude_score', 0)), 
                reverse=True
            )
            
            st.divider()
            st.caption(f"🧠 {len(filtered_memories)} Intelligence Items (Filtrati da {len(memories)})")
            
            # 2-column Tile Grid
            cols = st.columns(2)
            
            for idx, item in enumerate(filtered_memories):
                meta = item['metadata']
                rel_score = int(meta.get('relevance_score', 0))
                mag_score = int(meta.get('magnitude_score', 0))
                strategy = meta.get('strategy', 'N/A').lower()
                
                # Visual Cues
                is_video = "youtube" in meta.get('link', '').lower() or "[video]" in meta.get('title', '').lower()
                video_badge = '<span class="video-badge">▶ VIDEO</span>' if is_video else ''
                
                # Truncate title if too long
                title = meta.get('title', 'Untitled')
                if len(title) > 80:
                    title = title[:77] + "..."
                title = html.escape(title)  # Escape HTML chars
                
                # Truncate reason
                reason = meta.get('relevance_reason', '') or meta.get('magnitude_reason', '') or ''
                if len(reason) > 120:
                    reason = reason[:117] + "..."
                reason = html.escape(reason)  # Escape HTML chars
                
                # Source and date
                source = meta.get('source', 'Unknown')
                pub_date = meta.get('published_at', '')[:10] if meta.get('published_at') else ''
                
                # Build tile HTML (no leading whitespace to avoid code block interpretation)
                tile_html = f'''<div class="news-tile {strategy}">
<div class="tile-title"><a href="{meta.get('link', '#')}" target="_blank">{title}</a> {video_badge}</div>
<div class="tile-meta">{source} • {pub_date}</div>
<div><span class="score-badge relevance">🛡️ {rel_score}/10</span><span class="score-badge magnitude">🌍 {mag_score}/10</span></div>
<div class="tile-reason">{reason}</div>
</div>'''
                
                # Place in alternating columns
                with cols[idx % 2]:
                    st.markdown(tile_html, unsafe_allow_html=True)

    # Footer
    st.divider()
    mode = "Live prices" if use_live else "DB prices"
    st.caption(f"🎯 War Room v4 • {mode} • {len(holdings)} holdings")

if __name__ == "__main__":
    main()
