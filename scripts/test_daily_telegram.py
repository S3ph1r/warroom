"""
Quick test script for Daily Telegram Report
"""
import sys
import asyncio
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

async def test_daily_report():
    from services.scheduler_service import scheduled_daily_telegram_report
    print("Testing Daily Telegram Report...")
    result = await scheduled_daily_telegram_report()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_daily_report())
