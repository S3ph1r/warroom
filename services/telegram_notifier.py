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
