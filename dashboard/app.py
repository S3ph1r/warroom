"""
🎯 WAR ROOM - Main Dashboard
Personal Investment Management System
"""
import streamlit as st
import pandas as pd
from decimal import Decimal
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="War Room",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA FUNCTIONS
# ============================================================

@st.cache_data(ttl=300)
def get_sample_portfolio_data():
    """Return sample portfolio data for demonstration"""
    return pd.DataFrame([
        {"ticker": "AAPL", "name": "Apple Inc.", "quantity": 50, "avg_price": 150.00, "current_price": 178.50, "asset_class": "STOCK", "sector": "Technology"},
        {"ticker": "MSFT", "name": "Microsoft Corp.", "quantity": 30, "avg_price": 280.00, "current_price": 378.91, "asset_class": "STOCK", "sector": "Technology"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "quantity": 20, "avg_price": 120.00, "current_price": 141.80, "asset_class": "STOCK", "sector": "Technology"},
        {"ticker": "BTC-USD", "name": "Bitcoin", "quantity": 0.5, "avg_price": 35000.00, "current_price": 42500.00, "asset_class": "CRYPTO", "sector": "Crypto"},
        {"ticker": "ETH-USD", "name": "Ethereum", "quantity": 3.0, "avg_price": 2000.00, "current_price": 2250.00, "asset_class": "CRYPTO", "sector": "Crypto"},
        {"ticker": "VWCE.DE", "name": "Vanguard FTSE All-World", "quantity": 100, "avg_price": 95.00, "current_price": 108.50, "asset_class": "ETF", "sector": "Global"},
    ])


def calculate_portfolio_metrics(df: pd.DataFrame) -> dict:
    """Calculate portfolio KPIs from holdings dataframe"""
    df = df.copy()
    df["invested"] = df["quantity"] * df["avg_price"]
    df["current_value"] = df["quantity"] * df["current_price"]
    df["pnl"] = df["current_value"] - df["invested"]
    df["pnl_pct"] = (df["pnl"] / df["invested"]) * 100
    
    total_invested = df["invested"].sum()
    total_value = df["current_value"].sum()
    total_pnl = df["pnl"].sum()
    pnl_pct = (total_pnl / total_invested) * 100 if total_invested > 0 else 0
    
    return {
        "total_invested": total_invested,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "pnl_pct": pnl_pct,
        "positions": len(df),
        "df": df
    }


# ============================================================
# MAIN DASHBOARD
# ============================================================

def main():
    # Header
    st.markdown('<p class="main-header">🎯 THE WAR ROOM</p>', unsafe_allow_html=True)
    st.caption("Personal Investment Management System")
    st.divider()
    
    # Load data
    portfolio_df = get_sample_portfolio_data()
    metrics = calculate_portfolio_metrics(portfolio_df)
    
    # ==================== KPI CARDS ====================
    st.subheader("📊 Portfolio Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Net Worth",
            value=f"€{metrics['total_value']:,.2f}",
            delta=f"{metrics['pnl_pct']:.2f}%"
        )
    
    with col2:
        st.metric(
            label="📥 Total Invested",
            value=f"€{metrics['total_invested']:,.2f}"
        )
    
    with col3:
        delta_color = "normal" if metrics['total_pnl'] >= 0 else "inverse"
        st.metric(
            label="📊 Total P&L",
            value=f"€{metrics['total_pnl']:,.2f}",
            delta=f"{metrics['pnl_pct']:.2f}%",
            delta_color=delta_color
        )
    
    with col4:
        st.metric(
            label="📈 Positions",
            value=f"{metrics['positions']}"
        )
    
    st.divider()
    
    # ==================== CHARTS ====================
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("🎯 Asset Allocation")
        
        # Sunburst chart
        allocation_df = metrics["df"].copy()
        allocation_df["value"] = allocation_df["current_value"]
        
        fig = px.sunburst(
            allocation_df,
            path=["asset_class", "sector", "ticker"],
            values="value",
            color="pnl_pct",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("📊 P&L by Position")
        
        # Bar chart for P&L
        pnl_df = metrics["df"].sort_values("pnl", ascending=True)
        
        colors = ['green' if x >= 0 else 'red' for x in pnl_df['pnl']]
        
        fig = go.Figure(go.Bar(
            x=pnl_df['pnl'],
            y=pnl_df['ticker'],
            orientation='h',
            marker_color=colors,
            text=[f"€{x:,.0f}" for x in pnl_df['pnl']],
            textposition='outside'
        ))
        fig.update_layout(
            margin=dict(t=0, l=0, r=0, b=0),
            height=400,
            xaxis_title="P&L (€)",
            yaxis_title=""
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ==================== POSITIONS TABLE ====================
    st.subheader("🏆 All Positions")
    
    display_df = metrics["df"][["ticker", "name", "quantity", "avg_price", "current_price", "pnl", "pnl_pct", "asset_class"]].copy()
    display_df.columns = ["Ticker", "Name", "Qty", "Avg Price", "Current", "P&L €", "P&L %", "Class"]
    
    # Format columns
    st.dataframe(
        display_df.style.format({
            "Avg Price": "€{:.2f}",
            "Current": "€{:.2f}",
            "P&L €": "€{:,.2f}",
            "P&L %": "{:.2f}%",
            "Qty": "{:.4f}"
        }).apply(
            lambda x: ['background-color: #d4edda' if v > 0 else 'background-color: #f8d7da' if v < 0 else '' 
                      for v in x] if x.name == "P&L €" else [''] * len(x),
            axis=0
        ),
        use_container_width=True,
        hide_index=True
    )
    
    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.header("⚙️ Settings")
        
        st.subheader("🔄 Data Source")
        data_source = st.radio(
            "Select source:",
            ["Demo Data", "Live Database"],
            index=0
        )
        
        if data_source == "Live Database":
            st.warning("⚠️ Connect database to see real data")
        
        st.divider()
        
        st.subheader("📊 Quick Stats")
        st.write(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")
        st.write(f"**Database:** PostgreSQL 16")
        st.write(f"**AI Engine:** Ollama (pending)")
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        st.caption("🎯 War Room v0.1.0")
        st.caption("Made with Streamlit")


if __name__ == "__main__":
    main()
