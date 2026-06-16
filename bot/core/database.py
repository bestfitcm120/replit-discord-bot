import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool(database_url: str) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        logger.info("Database connection pool created")
        await _ensure_schema(_pool)
    return _pool


async def _ensure_schema(pool: asyncpg.Pool) -> None:
    """
    Idempotently applies any schema changes the bot depends on.
    Uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS so it is safe to run on
    every startup against both fresh and existing databases.
    """
    async with pool.acquire() as conn:
        # ── Core tables (created by Drizzle on first dev push, but production
        #    Docker databases may be initialised without running the Node toolchain)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_configs (
                guild_id             TEXT PRIMARY KEY,
                default_log_channel  TEXT,
                log_channels         JSONB NOT NULL DEFAULT '{}',
                creation_voice_channel TEXT,
                updated_at           TIMESTAMPTZ
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                id          BIGSERIAL PRIMARY KEY,
                guild_id    TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                user_id     TEXT,
                target_id   TEXT,
                description TEXT NOT NULL,
                metadata    JSONB NOT NULL DEFAULT '{}',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS member_events (
                id          BIGSERIAL PRIMARY KEY,
                guild_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS message_stats (
                guild_id    TEXT NOT NULL,
                channel_id  TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                is_bot      BOOLEAN NOT NULL DEFAULT FALSE,
                stat_date   DATE NOT NULL,
                count       INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, channel_id, user_id, stat_date)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_voice_channels (
                channel_id  TEXT PRIMARY KEY,
                guild_id    TEXT NOT NULL,
                owner_id    TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # ── Column additions for databases that existed before these fields
        #    were added (ALTER TABLE ... ADD COLUMN IF NOT EXISTS is idempotent)
        await conn.execute("""
            ALTER TABLE guild_configs
                ADD COLUMN IF NOT EXISTS creation_voice_channel TEXT
        """)

    logger.info("Database schema verified / migrated successfully")


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


# ──────────────────────────────────────────────────────────────────────────────
# Temp voice channel helpers
# ──────────────────────────────────────────────────────────────────────────────

async def get_creation_voice_channel(pool: asyncpg.Pool, guild_id: str) -> Optional[str]:
    """Return the configured creation voice channel ID for this guild, or None."""
    row = await pool.fetchrow(
        "SELECT creation_voice_channel FROM guild_configs WHERE guild_id = $1",
        guild_id,
    )
    return row["creation_voice_channel"] if row else None


async def add_temp_channel(
    pool: asyncpg.Pool,
    channel_id: str,
    guild_id: str,
    owner_id: str,
) -> None:
    await pool.execute(
        """
        INSERT INTO temp_voice_channels (channel_id, guild_id, owner_id, created_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (channel_id) DO NOTHING
        """,
        channel_id,
        guild_id,
        owner_id,
    )


async def remove_temp_channel(pool: asyncpg.Pool, channel_id: str) -> None:
    await pool.execute(
        "DELETE FROM temp_voice_channels WHERE channel_id = $1",
        channel_id,
    )


async def is_temp_channel(pool: asyncpg.Pool, channel_id: str) -> bool:
    row = await pool.fetchrow(
        "SELECT 1 FROM temp_voice_channels WHERE channel_id = $1",
        channel_id,
    )
    return row is not None


async def get_temp_channel_owner(pool: asyncpg.Pool, channel_id: str) -> Optional[str]:
    row = await pool.fetchrow(
        "SELECT owner_id FROM temp_voice_channels WHERE channel_id = $1",
        channel_id,
    )
    return row["owner_id"] if row else None


async def get_all_temp_channels(pool: asyncpg.Pool) -> list[dict]:
    """Return all tracked temp channels (used for startup cleanup)."""
    rows = await pool.fetch("SELECT channel_id, guild_id, owner_id FROM temp_voice_channels")
    return [dict(r) for r in rows]
