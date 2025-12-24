"""
WAR ROOM - Scheduled Tasks Service
Uses APScheduler for automated background jobs.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def scheduled_intelligence_scan():
    """Runs the Intelligence Engine scan as a scheduled task."""
    from intelligence.engine import IntelligenceEngine
    from services.portfolio_service import get_all_holdings
    
    logger.info(f"[SCHEDULER] Starting scheduled Intelligence Scan at {datetime.now().strftime('%H:%M')}")
    
    try:
        # Build portfolio context
        holdings = get_all_holdings()
        tickers = ", ".join([h.get('ticker', '') for h in holdings[:15]]) if holdings else ""
        context = f"Portfolio: {tickers}"
        
        engine = IntelligenceEngine(portfolio_context=context)
        new_items = engine.run_cycle()
        
        logger.info(f"[SCHEDULER] Scan complete. Found {len(new_items)} new items.")
        return len(new_items)
    except Exception as e:
        logger.error(f"[SCHEDULER] Scan failed: {e}")
        return 0


def setup_scheduled_jobs():
    """Configure all scheduled jobs. Called once at app startup."""
    
    # Morning scan (08:00 CET)
    scheduler.add_job(
        scheduled_intelligence_scan,
        CronTrigger(hour=8, minute=0),
        id="morning_scan",
        name="Morning Intelligence Scan",
        replace_existing=True
    )
    
    # Evening scan (18:00 CET)
    scheduler.add_job(
        scheduled_intelligence_scan,
        CronTrigger(hour=18, minute=0),
        id="evening_scan", 
        name="Evening Intelligence Scan",
        replace_existing=True
    )
    
    # Alert checking every 5 minutes during market hours (8:00-22:00)
    scheduler.add_job(
        scheduled_alert_check,
        CronTrigger(minute='*/5', hour='8-22'),
        id="alert_check",
        name="Price Alert Check (every 5 min)",
        replace_existing=True
    )
    
    # Daily portfolio snapshot at 22:00 CET (after market close)
    scheduler.add_job(
        scheduled_daily_snapshot,
        CronTrigger(hour=22, minute=0),
        id="daily_snapshot",
        name="Portfolio Daily Snapshot",
        replace_existing=True
    )
    
    logger.info("[SCHEDULER] Scheduled jobs configured: 08:00/18:00 scans, 5-min alerts, 22:00 snapshot")


async def scheduled_alert_check():
    """Runs alert checking as a scheduled task."""
    from services.alert_engine import check_alerts
    
    logger.info(f"[SCHEDULER] Checking price alerts...")
    try:
        triggered = await check_alerts()
        if triggered:
            logger.info(f"[SCHEDULER] {len(triggered)} alert(s) triggered!")
        return len(triggered)
    except Exception as e:
        logger.error(f"[SCHEDULER] Alert check failed: {e}")
        return 0


async def scheduled_daily_snapshot():
    """Saves a daily portfolio snapshot at 22:00."""
    from services.analytics_service import save_daily_snapshot
    
    logger.info(f"[SCHEDULER] Saving daily portfolio snapshot...")
    try:
        result = save_daily_snapshot()
        logger.info(f"[SCHEDULER] Snapshot saved: {result}")
        return result
    except Exception as e:
        logger.error(f"[SCHEDULER] Snapshot failed: {e}")
        return None


def get_scheduled_jobs():
    """Returns list of scheduled jobs for API/UI display."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    return jobs


def start_scheduler():
    """Start the scheduler. Call this in FastAPI startup event."""
    if not scheduler.running:
        setup_scheduled_jobs()
        scheduler.start()
        logger.info("[SCHEDULER] Scheduler started.")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[SCHEDULER] Scheduler stopped.")
