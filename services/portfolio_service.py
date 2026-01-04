"""
WAR ROOM - Portfolio Service v2
Queries data from the new holdings-based schema.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import func
from db.database import SessionLocal
from db.models import Holding, Transaction


class PortfolioService:
    """
    Service for portfolio analytics using the new schema.
    """
    
    def __init__(self):
        self.session = SessionLocal()
    
    def close(self):
        self.session.close()

    def get_anonymous_portfolio_context(self) -> dict:
        """
        Generates an anonymized (percentage-based) portfolio summary for AI Council.
        Masks absolute Euro values.
        """
        total_value = self.get_total_value()
        if total_value == 0:
            return {"error": "Portfolio is empty"}

        holdings = self.session.query(Holding).all()
        
        # 1. Asset Allocation (by Type)
        by_type_raw = self.get_value_by_asset_type()
        allocation = {k: round(float(v / total_value) * 100, 2) for k, v in by_type_raw.items()}
        
        # 2. Top Positions (by Weight)
        positions = []
        for h in holdings:
            weight = (h.current_value / total_value) * 100
            positions.append({
                "ticker": h.ticker,
                "name": h.name,
                "type": h.asset_type,
                "weight_pct": round(float(weight), 2)
            })
        
        # Sort by weight desc and take top 15
        positions.sort(key=lambda x: x['weight_pct'], reverse=True)
        top_positions = positions[:15]
        
        # 3. Currency Exposure
        currencies = {}
        for h in holdings:
            curr = h.currency
            currencies[curr] = currencies.get(curr, 0) + h.current_value
        currency_exposure = {k: round(float(v / total_value) * 100, 2) for k, v in currencies.items()}

        return {
            "total_value_masked": "CONFIDENTIAL",
            "allocation": allocation,
            "currency_exposure": currency_exposure,
            "top_holdings": top_positions,
            "note": "Values are percentage weights of Total Portfolio."
        }
    
    # =========================================
    # AGGREGATES
    # =========================================
    
    def get_total_value(self) -> Decimal:
        """Get total portfolio value across all brokers."""
        result = self.session.query(
            func.sum(Holding.current_value)
        ).scalar()
        return result or Decimal("0")
    
    def get_value_by_broker(self) -> Dict[str, Decimal]:
        """Get portfolio value grouped by broker."""
        results = self.session.query(
            Holding.broker,
            func.sum(Holding.current_value).label("total")
        ).group_by(Holding.broker).all()
        
        return {r.broker: r.total for r in results}
    
    def get_value_by_asset_type(self) -> Dict[str, Decimal]:
        """Get portfolio value grouped by asset type."""
        results = self.session.query(
            Holding.asset_type,
            func.sum(Holding.current_value).label("total")
        ).group_by(Holding.asset_type).all()
        
        return {r.asset_type: r.total for r in results}
    
    # =========================================
    # HOLDINGS
    # =========================================
    
    def get_all_holdings(self) -> List[dict]:
        """Get all holdings as list of dicts."""
        holdings = self.session.query(Holding).all()
        return [
            {
                "id": str(h.id),
                "broker": h.broker,
                "ticker": h.ticker,
                "isin": h.isin,
                "name": h.name,
                "asset_type": h.asset_type,
                "quantity": float(h.quantity),
                "current_price": float(h.current_price) if h.current_price else 0,
                "purchase_price": float(h.purchase_price) if h.purchase_price else 0,
                "current_value": float(h.current_value),
                "currency": h.currency,
                "source_document": h.source_document,
                "last_updated": h.last_updated.isoformat() if h.last_updated else None,
                "share_class": h.share_class,
                "adr_ratio": h.adr_ratio,
                "nominal_value": h.nominal_value,
                "market": h.market,
            }
            for h in holdings
        ]
    
    def get_holdings_by_broker(self, broker: str) -> List[dict]:
        """Get holdings for a specific broker."""
        holdings = self.session.query(Holding).filter(
            Holding.broker == broker
        ).all()
        return [
            {
                "ticker": h.ticker,
                "isin": h.isin,
                "name": h.name,
                "asset_type": h.asset_type,
                "quantity": float(h.quantity),
                "current_price": float(h.current_price) if h.current_price else 0,
                "current_value": float(h.current_value),
                "currency": h.currency,
            }
            for h in holdings
        ]
    
    def get_brokers(self) -> List[str]:
        """Get list of all brokers with holdings."""
        results = self.session.query(Holding.broker).distinct().all()
        return [r[0] for r in results]
    
    def get_holdings_count(self) -> int:
        """Get total number of holdings."""
        return self.session.query(Holding).count()
    
    # =========================================
    # SUMMARY
    # =========================================
    
    def get_portfolio_summary(self) -> dict:
        """Get complete portfolio summary."""
        total_value = self.get_total_value()
        by_broker = self.get_value_by_broker()
        by_type = self.get_value_by_asset_type()
        holdings_count = self.get_holdings_count()
        brokers = self.get_brokers()
        
        return {
            "total_value": float(total_value),
            "holdings_count": holdings_count,
            "brokers_count": len(brokers),
            "brokers": brokers,
            "by_broker": {k: float(v) for k, v in by_broker.items()},
            "by_asset_type": {k: float(v) for k, v in by_type.items()},
        }


# =========================================
# UTILITY FUNCTIONS
# =========================================

def get_portfolio_summary() -> dict:
    """Convenience function to get portfolio summary."""
    service = PortfolioService()
    summary = service.get_portfolio_summary()
    service.close()
    return summary


def get_all_holdings() -> List[dict]:
    """Convenience function to get all holdings."""
    service = PortfolioService()
    holdings = service.get_all_holdings()
    service.close()
    return holdings


def get_holdings_by_broker(broker: str) -> List[dict]:
    """Convenience function to get holdings for a broker."""
    service = PortfolioService()
    holdings = service.get_holdings_by_broker(broker)
    service.close()
    return holdings

def get_anonymous_portfolio_context() -> dict:
    """Convenience function for Council Context."""
    service = PortfolioService()
    ctx = service.get_anonymous_portfolio_context()
    service.close()
    return ctx

