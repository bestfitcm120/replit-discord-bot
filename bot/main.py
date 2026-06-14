"""
Discord Moderation Bot — entry point.

Environment variables required:
  DISCORD_TOKEN   — your bot token
  DATABASE_URL    — PostgreSQL connection string
  BOT_PREFIX      — command prefix (default: !)
  WEB_API_URL     — internal URL of the web API (default: http://web:8000)
"""
import asyncio
import logging
import sys

from bot.core.bot import ModerationBot
from bot.core.config import BotConfig
from bot.core.database import close_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    config = BotConfig.from_env()
    bot = ModerationBot(config)

    try:
        await bot.start(config.token)
    except KeyboardInterrupt:
        logger.info("Shutting down…")
    finally:
        await close_pool()
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
