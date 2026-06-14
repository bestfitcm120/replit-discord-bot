import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool(database_url: str) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        logger.info("Database connection pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def get_log_channel(pool: asyncpg.Pool, guild_id: str, event_type: str) -> Optional[str]:
    """
    Returns the channel ID for a given event type.
    Falls back to the default log channel if no specific channel is set.
    """
    row = await pool.fetchrow(
        """
        SELECT
            log_channels->$2 AS specific_channel,
            default_log_channel
        FROM guild_configs
        WHERE guild_id = $1
        """,
        guild_id,
        event_type,
    )
    if not row:
        return None

    specific = row["specific_channel"]
    if specific and specific.strip('"') and specific.strip('"') != "null":
        channel_id = specific.strip('"')
        return channel_id if channel_id else None

    default = row["default_log_channel"]
    return default if default else None


async def insert_log_entry(
    pool: asyncpg.Pool,
    guild_id: str,
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    import json
    await pool.execute(
        """
        INSERT INTO log_entries (guild_id, event_type, user_id, target_id, description, metadata, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """,
        guild_id,
        event_type,
        user_id,
        target_id,
        description,
        json.dumps(metadata or {}),
    )


async def track_member_event(
    pool: asyncpg.Pool,
    guild_id: str,
    user_id: str,
    event_type: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO member_events (guild_id, user_id, event_type, created_at)
        VALUES ($1, $2, $3, NOW())
        """,
        guild_id,
        user_id,
        event_type,
    )


async def track_message_event(
    pool: asyncpg.Pool,
    guild_id: str,
    channel_id: str,
    user_id: str,
    is_bot: bool,
) -> None:
    today = __import__("datetime").date.today()
    await pool.execute(
        """
        INSERT INTO message_stats (guild_id, channel_id, user_id, is_bot, stat_date, count)
        VALUES ($1, $2, $3, $4, $5, 1)
        ON CONFLICT (guild_id, channel_id, user_id, stat_date)
        DO UPDATE SET count = message_stats.count + 1
        """,
        guild_id,
        channel_id,
        user_id,
        is_bot,
        today,
    )
