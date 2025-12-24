"""
WAR ROOM - Analytics Service
Handles portfolio snapshots, performance tracking, and risk metrics.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
import numpy as np

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Holding, PortfolioSnapshot

logger = logging.getLogger(__name__)

# Benchmark tickers
BENCHMARKS = {
    "SP500": "^GSPC",
    "NASDAQ100": "^NDX",
    "MSCI_WORLD": "URTH"  # ETF proxy for MSCI World
}


def save_daily_snapshot() -> Dict:
    """
    Save a daily snapshot of the portfolio.
    Called by scheduler at 22:00 CET or manually via API.
    """
    db = SessionLocal()
    try:
        today = date.today()
        
        # Check if snapshot already exists for today
        existing = db.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
        ).scalar_one_or_none()
        
        if existing:
            logger.info(f"[ANALYTICS] Snapshot already exists for {today}, updating...")
            snapshot = existing
        else:
            snapshot = PortfolioSnapshot(snapshot_date=today)
        
        # Get all holdings
        holdings = db.execute(select(Holding)).scalars().all()
        
        if not holdings:
            logger.warning("[ANALYTICS] No holdings found, skipping snapshot")
            return {"status": "skipped", "reason": "no_holdings"}
        
        # Calculate totals
        total_value = Decimal("0")
        total_cost = Decimal("0")
        broker_breakdown = {}
        asset_breakdown = {}
        
        for h in holdings:
            value = h.current_value or Decimal("0")
            cost = (h.purchase_price or Decimal("0")) * h.quantity
            
            total_value += value
            total_cost += cost
            
            # Broker breakdown
            broker = h.broker or "UNKNOWN"
            broker_breakdown[broker] = float(broker_breakdown.get(broker, 0)) + float(value)
            
            # Asset type breakdown
            asset_type = h.asset_type or "OTHER"
            asset_breakdown[asset_type] = float(asset_breakdown.get(asset_type, 0)) + float(value)
        
        # Calculate P&L
        pnl_net = total_value - total_cost
        pnl_pct = (pnl_net / total_cost * 100) if total_cost > 0 else Decimal("0")
        
        # Update snapshot
        snapshot.total_value = total_value
        snapshot.total_cost = total_cost
        snapshot.pnl_net = pnl_net
        snapshot.pnl_pct = pnl_pct
        snapshot.broker_breakdown = broker_breakdown
        snapshot.asset_breakdown = asset_breakdown
        snapshot.holdings_count = len(holdings)
        
        if not existing:
            db.add(snapshot)
        
        db.commit()
        
        logger.info(f"[ANALYTICS] Snapshot saved: {today} - Value: €{total_value:.2f}")
        
        return {
            "status": "saved",
            "date": str(today),
            "total_value": float(total_value),
            "pnl_net": float(pnl_net),
            "holdings_count": len(holdings)
        }
        
    except Exception as e:
        logger.error(f"[ANALYTICS] Error saving snapshot: {e}")
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def get_portfolio_history(days: int = 30) -> List[Dict]:
    """
    Get portfolio value history for the last N days.
    """
    db = SessionLocal()
    try:
        cutoff = date.today() - timedelta(days=days)
        
        snapshots = db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= cutoff)
            .order_by(PortfolioSnapshot.snapshot_date)
        ).scalars().all()
        
        return [
            {
                "date": str(s.snapshot_date),
                "value": float(s.total_value),
                "pnl_net": float(s.pnl_net),
                "pnl_pct": float(s.pnl_pct)
            }
            for s in snapshots
        ]
        
    finally:
        db.close()


def get_benchmark_history(days: int = 30) -> Dict[str, List[Dict]]:
    """
    Get benchmark performance for comparison.
    Returns normalized returns (percentage change from start).
    """
    result = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for name, ticker in BENCHMARKS.items():
        try:
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True
            )
            
            if data.empty:
                logger.warning(f"[ANALYTICS] No data for benchmark {name}")
                continue
            
            # Get closing prices
            closes = data["Close"]
            
            # Handle DataFrame vs Series (yfinance update fix)
            if isinstance(closes, pd.DataFrame):
                closes = closes.iloc[:, 0]
                
            closes = closes.dropna()
            if len(closes) == 0:
                continue
                
            # Normalize to percentage change from first value
            # Handle potential scale/series issues
            first_val = closes.iloc[0]
            if hasattr(first_val, 'item'):
                first_value = float(first_val.item())
            else:
                first_value = float(first_val)
                
            result[name] = []
            
            for idx, price in closes.items():
                # Safe extraction of value
                if hasattr(price, 'item'):
                    price_val = float(price.item())
                else:
                    price_val = float(price)
                
                # Normalize date
                # idx is likely a Timestamp, so .date() is valid
                # If idx is wrong type, we catch it
                if hasattr(idx, 'date'):
                    date_str = str(idx.date())
                else:
                    date_str = str(idx).split(" ")[0]
                
                result[name].append({
                    "date": date_str,
                    "value": price_val,
                    "pct_change": ((price_val / first_value) - 1) * 100
                })
            
        except Exception as e:
            logger.error(f"[ANALYTICS] Error fetching {name}: {e}")
    
    return result


def calculate_risk_metrics() -> Dict:
    """
    Calculate risk metrics based on portfolio history.
    Returns Sharpe ratio, volatility, and max drawdown.
    """
    db = SessionLocal()
    try:
        # Get last 365 days of snapshots
        cutoff = date.today() - timedelta(days=365)
        
        snapshots = db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= cutoff)
            .order_by(PortfolioSnapshot.snapshot_date)
        ).scalars().all()
        
        if len(snapshots) < 2:
            return {
                "sharpe_ratio": None,
                "volatility": None,
                "max_drawdown": None,
                "message": "Insufficient data (need at least 2 snapshots)"
            }
        
        # Extract values
        values = [float(s.total_value) for s in snapshots]
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                daily_return = (values[i] - values[i-1]) / values[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return {
                "sharpe_ratio": None,
                "volatility": None,
                "max_drawdown": None,
                "message": "Insufficient return data"
            }
        
        returns_array = np.array(returns)
        
        # Volatility (annualized)
        daily_vol = np.std(returns_array)
        annual_vol = daily_vol * np.sqrt(252)
        
        # Sharpe Ratio (assuming risk-free rate of 4%)
        risk_free_rate = 0.04
        mean_return = np.mean(returns_array) * 252  # Annualized
        sharpe = (mean_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
        
        # Max Drawdown
        peak = values[0]
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return {
            "sharpe_ratio": round(sharpe, 2),
            "volatility": round(annual_vol * 100, 2),  # As percentage
            "max_drawdown": round(max_dd * 100, 2),    # As percentage
            "data_points": len(snapshots),
            "period_days": (snapshots[-1].snapshot_date - snapshots[0].snapshot_date).days
        }
        
    finally:
        db.close()


def get_latest_snapshot() -> Optional[Dict]:
    """Get the most recent snapshot."""
    db = SessionLocal()
    try:
        snapshot = db.execute(
            select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)
        ).scalar_one_or_none()
        
        if not snapshot:
            return None
            
        return {
            "date": str(snapshot.snapshot_date),
            "total_value": float(snapshot.total_value),
            "total_cost": float(snapshot.total_cost),
            "pnl_net": float(snapshot.pnl_net),
            "pnl_pct": float(snapshot.pnl_pct),
            "broker_breakdown": snapshot.broker_breakdown,
            "asset_breakdown": snapshot.asset_breakdown,
            "holdings_count": snapshot.holdings_count
        }
    finally:
        db.close()
