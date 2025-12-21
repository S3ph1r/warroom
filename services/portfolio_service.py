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
