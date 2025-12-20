"""
🎯 WAR ROOM - Main Dashboard v2
Personal Investment Management System
Uses the new holdings-based schema
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Page configuration
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
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .broker-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        color: white;
        margin-bottom: 1rem;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA FUNCTIONS
# ============================================================

@st.cache_data(ttl=60)
def get_portfolio_data():
    """Get portfolio data from new holdings table."""
    try:
        from services.portfolio_service import get_portfolio_summary, get_all_holdings
        
        summary = get_portfolio_summary()
        holdings = get_all_holdings()
        
        return {
            "summary": summary,
            "holdings": holdings
        }
    except Exception as e:
        st.error(f"Database error: {e}")
        return None


def get_holdings_dataframe(holdings: list) -> pd.DataFrame:
    """Convert holdings list to DataFrame."""
    if not holdings:
        return pd.DataFrame()
    
    df = pd.DataFrame(holdings)
    
    # Rename columns for display
    df = df.rename(columns={
        "broker": "Broker",
        "ticker": "Ticker",
        "name": "Name",
        "asset_type": "Type",
        "quantity": "Qty",
        "current_price": "Price",
        "current_value": "Value",
        "currency": "Currency",
        "source_document": "Source"
    })
    
    return df


# ============================================================
# MAIN DASHBOARD
# ============================================================

def main():
    # Header
    st.markdown('<p class="main-header">🎯 THE WAR ROOM</p>', unsafe_allow_html=True)
    st.caption("Personal Investment Management System")
    st.divider()
    
    # Load data
    with st.spinner("Loading portfolio data..."):
        data = get_portfolio_data()
    
    if not data:
        st.error("❌ Failed to load portfolio data. Check database connection.")
        return
    
    summary = data["summary"]
    holdings = data["holdings"]
    
    # ==================== KPI CARDS ====================
    st.subheader("📊 Portfolio Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Net Worth",
            value=f"€{summary['total_value']:,.2f}"
        )
    
    with col2:
        st.metric(
            label="📈 Holdings",
            value=f"{summary['holdings_count']}"
        )
    
    with col3:
        st.metric(
            label="🏦 Brokers",
            value=f"{summary['brokers_count']}"
        )
    
    with col4:
        # Top asset type
        if summary.get('by_asset_type'):
            top_type = max(summary['by_asset_type'], key=summary['by_asset_type'].get)
            top_value = summary['by_asset_type'][top_type]
            st.metric(
                label=f"📊 Top: {top_type}",
                value=f"€{top_value:,.2f}"
            )
    
    st.divider()
    
    # ==================== BROKER BREAKDOWN ====================
    st.subheader("🏦 Portfolio by Broker")
    
    broker_data = summary.get('by_broker', {})
    if broker_data:
        # Sort by value
        sorted_brokers = sorted(broker_data.items(), key=lambda x: x[1], reverse=True)
        
        cols = st.columns(len(sorted_brokers))
        for i, (broker, value) in enumerate(sorted_brokers):
            with cols[i]:
                pct = (value / summary['total_value'] * 100) if summary['total_value'] > 0 else 0
                st.metric(
                    label=broker.replace("_", " "),
                    value=f"€{value:,.2f}",
                    delta=f"{pct:.1f}%"
                )
    
    st.divider()
    
    # ==================== CHARTS ====================
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("🎯 Allocation by Broker")
        
        if broker_data:
            broker_df = pd.DataFrame([
                {"Broker": k.replace("_", " "), "Value": v}
                for k, v in broker_data.items()
            ])
            
            fig = px.pie(
                broker_df,
                values="Value",
                names="Broker",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("📊 Allocation by Asset Type")
        
        type_data = summary.get('by_asset_type', {})
        if type_data:
            type_df = pd.DataFrame([
                {"Type": k, "Value": v}
                for k, v in type_data.items()
            ])
            
            fig = px.bar(
                type_df.sort_values("Value", ascending=True),
                x="Value",
                y="Type",
                orientation='h',
                color="Type",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                margin=dict(t=0, l=0, r=0, b=0),
                height=350,
                showlegend=False,
                xaxis_title="Value (€)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ==================== HOLDINGS TABLE ====================
    st.subheader("🏆 All Holdings")
    
    # Broker filter
    selected_broker = st.selectbox(
        "Filter by broker:",
        ["All Brokers"] + summary.get('brokers', []),
        index=0
    )
    
    # Create dataframe
    df = get_holdings_dataframe(holdings)
    
    if not df.empty:
        # Filter by broker
        if selected_broker != "All Brokers":
            df = df[df["Broker"] == selected_broker]
        
        # Sort by value
        df = df.sort_values("Value", ascending=False)
        
        # Display
        display_cols = ["Ticker", "Name", "Type", "Broker", "Qty", "Value", "Source"]
        display_df = df[display_cols].copy()
        
        # Format
        display_df["Value"] = display_df["Value"].apply(lambda x: f"€{x:,.2f}")
        display_df["Qty"] = display_df["Qty"].apply(lambda x: f"{x:,.4f}" if x < 10 else f"{x:,.2f}")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Summary below table
        if selected_broker != "All Brokers":
            broker_total = broker_data.get(selected_broker, 0)
            st.info(f"**{selected_broker}**: €{broker_total:,.2f} ({len(df)} holdings)")
    
    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.header("⚙️ War Room")
        
        st.subheader("📊 Quick Stats")
        st.write(f"**Total Value:** €{summary['total_value']:,.2f}")
        st.write(f"**Holdings:** {summary['holdings_count']}")
        st.write(f"**Brokers:** {summary['brokers_count']}")
        st.write(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        st.subheader("🏦 Brokers")
        for broker in summary.get('brokers', []):
            value = broker_data.get(broker, 0)
            st.write(f"• {broker.replace('_', ' ')}: €{value:,.2f}")
        
        st.divider()
        
        st.caption("🎯 War Room v2.0")
        st.caption("Built with Streamlit + PostgreSQL")


if __name__ == "__main__":
    main()
