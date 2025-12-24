"""
WAR ROOM - Alert Engine Service
Monitors prices and triggers alerts when thresholds are crossed.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict

from db.database import SessionLocal
from db.models import PriceAlert
from services.price_service_v5 import get_live_price_for_ticker

logger = logging.getLogger(__name__)


def get_active_alerts() -> List[Dict]:
    """Returns all active (non-triggered) alerts."""
    db = SessionLocal()
    try:
        alerts = db.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        return [
            {
                "id": str(a.id),
                "ticker": a.ticker,
                "name": a.name,
                "target_price": float(a.target_price),
                "direction": a.direction,
                "notify_telegram": a.notify_telegram,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in alerts
        ]
    finally:
        db.close()


def create_alert(ticker: str, target_price: float, direction: str, name: str = None, notify_telegram: bool = True) -> Dict:
    """Creates a new price alert."""
    db = SessionLocal()
    try:
        alert = PriceAlert(
            ticker=ticker.upper(),
            name=name or ticker.upper(),
            target_price=Decimal(str(target_price)),
            direction=direction.lower(),
            notify_telegram=notify_telegram,
            is_active=True
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"Created alert for {ticker} @ ${target_price} ({direction})")
        
        return {
            "id": str(alert.id),
            "ticker": alert.ticker,
            "target_price": float(alert.target_price),
            "direction": alert.direction,
            "created_at": alert.created_at.isoformat()
        }
    finally:
        db.close()


def delete_alert(alert_id: str) -> bool:
    """Deletes an alert by ID."""
    db = SessionLocal()
    try:
        from uuid import UUID
        alert = db.query(PriceAlert).filter(PriceAlert.id == UUID(alert_id)).first()
        if alert:
            db.delete(alert)
            db.commit()
            logger.info(f"Deleted alert {alert_id}")
            return True
        return False
    finally:
        db.close()


async def check_alerts() -> List[Dict]:
    """
    Checks all active alerts against current prices.
    Triggers notifications for any crossed thresholds.
    Returns list of triggered alerts.
    """
    triggered = []
    db = SessionLocal()
    
    try:
        alerts = db.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        
        for alert in alerts:
            try:
                # Get current price (using existing price service)
                price_data = get_live_price_for_ticker(alert.ticker)
                if not price_data:
                    continue
                
                current_price = price_data.get("price", 0)
                if current_price <= 0:
                    continue
                
                target = float(alert.target_price)
                should_trigger = False
                
                if alert.direction == "above" and current_price >= target:
                    should_trigger = True
                elif alert.direction == "below" and current_price <= target:
                    should_trigger = True
                
                if should_trigger:
                    # Mark as triggered
                    alert.is_active = False
                    alert.triggered_at = datetime.utcnow()
                    alert.triggered_price = Decimal(str(current_price))
                    
                    # Send notification
                    if alert.notify_telegram:
                        from services.telegram_notifier import send_price_alert
                        await send_price_alert(
                            ticker=alert.ticker,
                            current_price=current_price,
                            target_price=target,
                            direction=alert.direction
                        )
                    
                    triggered.append({
                        "ticker": alert.ticker,
                        "target": target,
                        "current": current_price,
                        "direction": alert.direction
                    })
                    
                    logger.info(f"Alert triggered: {alert.ticker} @ {current_price} (target: {target})")
                    
            except Exception as e:
                logger.error(f"Error checking alert for {alert.ticker}: {e}")
                continue
        
        db.commit()
        
    finally:
        db.close()
    
    return triggered
