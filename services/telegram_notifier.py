"""
WAR ROOM - Telegram Notifier Service
Sends notifications to user via Telegram Bot.
"""
import os
import logging
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Bot configuration (loaded from environment)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Your personal chat ID with the bot


async def send_telegram_message(message: str) -> bool:
    """
    Sends a message via Telegram Bot.
    Returns True if successful, False otherwise.
    """
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured. Skipping notification.")
        return False
    
    if not CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not configured. Skipping notification.")
        return False
    
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="HTML"
        )
        logger.info(f"Telegram notification sent successfully.")
        return True
    except TelegramError as e:
        logger.error(f"Telegram notification failed: {e}")
        return False


async def send_price_alert(ticker: str, current_price: float, target_price: float, direction: str) -> bool:
    """
    Sends a price alert notification with rich formatting.
    """
    emoji = "📈" if direction == "above" else "📉"
    arrow = "↑" if direction == "above" else "↓"
    
    message = f"""
🚨 <b>PRICE ALERT</b> 🚨

{emoji} <b>{ticker}</b> has crossed your target!

<b>Current Price:</b> ${current_price:.2f}
<b>Target Price:</b> ${target_price:.2f} ({arrow})
<b>Direction:</b> {direction.upper()}

━━━━━━━━━━━━━━━━━━━━
<i>War Room Alert System</i>
"""
    return await send_telegram_message(message)


async def send_council_alert(summary: str) -> bool:
    """
    Sends a Council session summary notification.
    """
    message = f"""
🏛️ <b>COUNCIL SESSION COMPLETE</b> 🏛️

{summary[:500]}...

━━━━━━━━━━━━━━━━━━━━
<i>War Room Council</i>
"""
    return await send_telegram_message(message)


async def send_daily_portfolio_report(
    net_worth: float,
    daily_pnl: float,
    daily_pnl_pct: float,
    top_mover_ticker: str = None,
    top_mover_pct: float = None,
    holdings_count: int = 0
) -> bool:
    """
    Sends the daily morning portfolio report.
    Called by scheduler at 08:00 CET.
    """
    # Format P&L with color emoji
    if daily_pnl >= 0:
        pnl_emoji = "🟢"
        pnl_sign = "+"
    else:
        pnl_emoji = "🔴"
        pnl_sign = ""
    
    # Format top mover
    if top_mover_ticker and top_mover_pct is not None:
        mover_emoji = "📈" if top_mover_pct >= 0 else "📉"
        mover_sign = "+" if top_mover_pct >= 0 else ""
        top_mover_line = f"\n<b>Top Mover:</b> {top_mover_ticker} ({mover_sign}{top_mover_pct:.1f}%) {mover_emoji}"
    else:
        top_mover_line = ""
    
    message = f"""
📊 <b>WAR ROOM Daily Report</b> 📊

<b>Net Worth:</b> €{net_worth:,.0f}
<b>Daily P&L:</b> {pnl_sign}€{abs(daily_pnl):,.0f} ({pnl_sign}{daily_pnl_pct:.2f}%) {pnl_emoji}{top_mover_line}
<b>Holdings:</b> {holdings_count} assets

━━━━━━━━━━━━━━━━━━━━
<i>Buona giornata di trading! 🚀</i>
"""
    return await send_telegram_message(message)

