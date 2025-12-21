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

# Page config
st.set_page_config(
    page_title="War Room",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stMetric > div {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 0.8rem;
        border: 1px solid #0f3460;
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
    
    # Footer
    st.divider()
    mode = "Live prices" if use_live else "DB prices"
    st.caption(f"🎯 War Room v4 • {mode} • {len(holdings)} holdings")


if __name__ == "__main__":
    main()
