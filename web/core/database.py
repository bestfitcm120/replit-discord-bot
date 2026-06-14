import asyncpg
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    database_url = os.environ.get("DATABASE_URL", "")
    _pool = await asyncpg.create_pool(database_url, min_size=2, max_size=20)
    logger.info("Database pool created")
    await _ensure_schema(_pool)
    yield
    if _pool:
        await _pool.close()
    logger.info("Database pool closed")


async def _ensure_schema(pool: asyncpg.Pool) -> None:
    """Create tables if they don't exist yet."""
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS guild_configs (
            guild_id        TEXT PRIMARY KEY,
            default_log_channel TEXT,
            log_channels    JSONB NOT NULL DEFAULT '{}',
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS log_entries (
            id          BIGSERIAL PRIMARY KEY,
            guild_id    TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            user_id     TEXT,
            target_id   TEXT,
            description TEXT NOT NULL,
            metadata    JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS log_entries_guild_id_idx ON log_entries(guild_id);
        CREATE INDEX IF NOT EXISTS log_entries_created_at_idx ON log_entries(created_at DESC);

        CREATE TABLE IF NOT EXISTS member_events (
            id          BIGSERIAL PRIMARY KEY,
            guild_id    TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS member_events_guild_id_idx ON member_events(guild_id);
        CREATE INDEX IF NOT EXISTS member_events_created_at_idx ON member_events(created_at DESC);

        CREATE TABLE IF NOT EXISTS message_stats (
            guild_id    TEXT NOT NULL,
            channel_id  TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            is_bot      BOOLEAN NOT NULL DEFAULT FALSE,
            stat_date   DATE NOT NULL,
            count       INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, channel_id, user_id, stat_date)
        );

        CREATE INDEX IF NOT EXISTS message_stats_guild_date_idx ON message_stats(guild_id, stat_date);
    """)
    logger.info("Database schema ensured")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
