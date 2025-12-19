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
    .broker-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA FUNCTIONS
# ============================================================

@st.cache_data(ttl=300)
def get_sample_portfolio_data():
    """Return sample portfolio data for demonstration"""
    return pd.DataFrame([
        {"ticker": "AAPL", "name": "Apple Inc.", "quantity": 50, "avg_price": 150.00, "current_price": 178.50, "asset_class": "STOCK", "sector": "Technology", "platform": "Demo"},
        {"ticker": "MSFT", "name": "Microsoft Corp.", "quantity": 30, "avg_price": 280.00, "current_price": 378.91, "asset_class": "STOCK", "sector": "Technology", "platform": "Demo"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "quantity": 20, "avg_price": 120.00, "current_price": 141.80, "asset_class": "STOCK", "sector": "Technology", "platform": "Demo"},
        {"ticker": "BTC-USD", "name": "Bitcoin", "quantity": 0.5, "avg_price": 35000.00, "current_price": 42500.00, "asset_class": "CRYPTO", "sector": "Crypto", "platform": "Demo"},
        {"ticker": "ETH-USD", "name": "Ethereum", "quantity": 3.0, "avg_price": 2000.00, "current_price": 2250.00, "asset_class": "CRYPTO", "sector": "Crypto", "platform": "Demo"},
        {"ticker": "VWCE.DE", "name": "Vanguard FTSE All-World", "quantity": 100, "avg_price": 95.00, "current_price": 108.50, "asset_class": "ETF", "sector": "Global", "platform": "Demo"},
    ])


@st.cache_data(ttl=60)
def get_real_portfolio_data():
    """Get real portfolio data from database"""
    try:
        from services.portfolio_service import PortfolioService
        
        service = PortfolioService()
        if not service.connect():
            return None
        
        try:
            summary = service.get_portfolio_summary()
            return summary
        finally:
            service.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        return None


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


def classify_asset(ticker: str) -> tuple:
    """Classify asset by ticker into asset_class and sector"""
    ticker_upper = ticker.upper()
    
    # Crypto patterns
    crypto_tokens = ['BTC', 'ETH', 'SOL', 'USDT', 'USDC', 'BNB', 'XRP', 'DOT', 'IOTA', 
                     'ENA', 'FET', 'MATIC', 'MANA', 'SAND', 'GALA', 'XLM', 'ADA',
                     'HMSTR', 'TON', 'DOGS', 'NOT', 'CATI', 'BB', 'LISTA']
    if any(token in ticker_upper for token in crypto_tokens):
        return 'CRYPTO', 'Crypto'
    
    # ETF patterns
    if 'ETF' in ticker_upper or ticker_upper.endswith('.DE') or 'VWCE' in ticker_upper:
        return 'ETF', 'Global'
    
    # Default to stock
    return 'STOCK', 'Equity'


# ============================================================
# MAIN DASHBOARD
# ============================================================

def main():
    # Header
    st.markdown('<p class="main-header">🎯 THE WAR ROOM</p>', unsafe_allow_html=True)
    st.caption("Personal Investment Management System")
    st.divider()
    
    # Sidebar - Data Source Selection
    with st.sidebar:
        st.header("⚙️ Settings")
        
        st.subheader("🔄 Data Source")
        data_source = st.radio(
            "Select source:",
            ["Live Database", "Demo Data"],
            index=0
        )
        
        st.divider()
    
    # Load data based on selection
    if data_source == "Live Database":
        with st.spinner("Loading data from database..."):
            db_data = get_real_portfolio_data()
        
        if db_data and db_data.get('holdings'):
            # Convert holdings to DataFrame
            holdings_list = []
            for h in db_data['holdings']:
                asset_class, sector = classify_asset(h['ticker'])
                holdings_list.append({
                    "ticker": h['ticker'],
                    "name": h['ticker'],  # Could enhance with asset registry
                    "quantity": h['quantity'],
                    "avg_price": h['avg_price'],
                    "current_price": h['avg_price'],  # TODO: Fetch live prices
                    "asset_class": asset_class,
                    "sector": sector,
                    "platform": ', '.join(h['platforms']) if h['platforms'] else 'Unknown'
                })
            
            if holdings_list:
                portfolio_df = pd.DataFrame(holdings_list)
                metrics = calculate_portfolio_metrics(portfolio_df)
                
                # Add database stats
                metrics['db_stats'] = {
                    'total_transactions': db_data.get('total_transactions', 0),
                    'by_platform': db_data.get('transactions_by_platform', {}),
                    'by_type': db_data.get('transactions_by_type', {}),
                    'first_tx': db_data.get('first_transaction'),
                    'last_tx': db_data.get('last_transaction'),
                    'total_dividends': db_data.get('total_dividends', 0),
                }
            else:
                st.warning("⚠️ No holdings found in database. Run import first.")
                portfolio_df = get_sample_portfolio_data()
                metrics = calculate_portfolio_metrics(portfolio_df)
        else:
            st.warning("⚠️ Cannot connect to database or no data. Showing demo data.")
            portfolio_df = get_sample_portfolio_data()
            metrics = calculate_portfolio_metrics(portfolio_df)
    else:
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
    
    # Show database stats if available
    if 'db_stats' in metrics:
        st.divider()
        st.subheader("📈 Transaction Statistics")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            st.metric("Total Transactions", f"{metrics['db_stats']['total_transactions']:,}")
        
        with col_b:
            st.metric("Total Dividends", f"€{metrics['db_stats']['total_dividends']:,.2f}")
        
        with col_c:
            if metrics['db_stats']['first_tx']:
                st.metric("First Transaction", metrics['db_stats']['first_tx'].strftime('%Y-%m-%d'))
        
        with col_d:
            if metrics['db_stats']['last_tx']:
                st.metric("Last Transaction", metrics['db_stats']['last_tx'].strftime('%Y-%m-%d'))
        
        # Platform breakdown
        if metrics['db_stats']['by_platform']:
            st.subheader("🏦 Transactions by Platform")
            platform_df = pd.DataFrame([
                {'Platform': k, 'Transactions': v} 
                for k, v in metrics['db_stats']['by_platform'].items()
            ])
            
            fig = px.pie(platform_df, values='Transactions', names='Platform', 
                        hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
    
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
        st.subheader("📊 Holdings by Value")
        
        # Bar chart for holdings by value
        value_df = metrics["df"].sort_values("current_value", ascending=True).tail(15)
        
        fig = go.Figure(go.Bar(
            x=value_df['current_value'],
            y=value_df['ticker'],
            orientation='h',
            marker_color='#1f77b4',
            text=[f"€{x:,.0f}" for x in value_df['current_value']],
            textposition='outside'
        ))
        fig.update_layout(
            margin=dict(t=0, l=0, r=0, b=0),
            height=400,
            xaxis_title="Value (€)",
            yaxis_title=""
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ==================== POSITIONS TABLE ====================
    st.subheader("🏆 All Positions")
    
    display_df = metrics["df"][["ticker", "name", "quantity", "avg_price", "current_price", "pnl", "pnl_pct", "asset_class"]].copy()
    if "platform" in metrics["df"].columns:
        display_df["platform"] = metrics["df"]["platform"]
    display_df.columns = ["Ticker", "Name", "Qty", "Avg Price", "Current", "P&L €", "P&L %", "Class"] + (["Platform"] if "platform" in metrics["df"].columns else [])
    
    # Format columns
    format_dict = {
        "Avg Price": "€{:.2f}",
        "Current": "€{:.2f}",
        "P&L €": "€{:,.2f}",
        "P&L %": "{:.2f}%",
        "Qty": "{:.4f}"
    }
    
    st.dataframe(
        display_df.style.format(format_dict).apply(
            lambda x: ['background-color: #d4edda' if v > 0 else 'background-color: #f8d7da' if v < 0 else '' 
                      for v in x] if x.name == "P&L €" else [''] * len(x),
            axis=0
        ),
        use_container_width=True,
        hide_index=True
    )
    
    # ==================== SIDEBAR CONTINUED ====================
    with st.sidebar:
        st.subheader("📊 Quick Stats")
        st.write(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")
        st.write(f"**Database:** PostgreSQL 16")
        st.write(f"**AI Engine:** Ollama (pending)")
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        # Import button
        if st.button("📥 Import New Data", use_container_width=True):
            st.info("Run: python scripts/import_all_data.py")
        
        st.divider()
        
        st.caption("🎯 War Room v0.2.0")
        st.caption("Made with Streamlit")


if __name__ == "__main__":
    main()
