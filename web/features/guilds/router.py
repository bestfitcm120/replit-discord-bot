import aiohttp
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Optional

from web.core.session import get_session

router = APIRouter()

DISCORD_API = "https://discord.com/api/v10"


def _require_session(request: Request) -> Optional[dict]:
    session = get_session(request)
    return session


def _guild_icon_url(guild_id: str, icon: Optional[str]) -> Optional[str]:
    if not icon:
        return None
    return f"https://cdn.discordapp.com/icons/{guild_id}/{icon}.png"


async def _fetch_user_guilds(access_token: str) -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            if resp.status != 200:
                return []
            return await resp.json()


async def _fetch_bot_guilds() -> set:
    """Return set of guild IDs the bot is in."""
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bot {bot_token}"},
        ) as resp:
            if resp.status != 200:
                return set()
            guilds = await resp.json()
            return {g["id"] for g in guilds}


async def _fetch_guild_channels(guild_id: str) -> list:
    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            headers={"Authorization": f"Bot {bot_token}"},
        ) as resp:
            if resp.status != 200:
                return []
            channels = await resp.json()
            return [
                {"id": c["id"], "name": c["name"], "type": c["type"]}
                for c in channels
                if c["type"] in (0, 2, 5)
            ]


@router.get("")
async def list_guilds(request: Request):
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    user_guilds = await _fetch_user_guilds(session["access_token"])
    bot_guild_ids = await _fetch_bot_guilds()

    MANAGE_GUILD = 0x20
    managed = [
        g for g in user_guilds
        if int(g["permissions"]) & MANAGE_GUILD or int(g["permissions"]) & 0x8
    ]

    return [
        {
            "id": g["id"],
            "name": g["name"],
            "icon": g.get("icon"),
            "iconUrl": _guild_icon_url(g["id"], g.get("icon")),
            "memberCount": 0,
            "botPresent": g["id"] in bot_guild_ids,
        }
        for g in managed
    ]


@router.get("/{guild_id}")
async def get_guild(guild_id: str, request: Request):
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    async with aiohttp.ClientSession() as http:
        async with http.get(
            f"{DISCORD_API}/guilds/{guild_id}?with_counts=true",
            headers={"Authorization": f"Bot {bot_token}"},
        ) as resp:
            if resp.status == 403:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
            if resp.status == 404:
                return JSONResponse({"error": "Guild not found"}, status_code=404)
            g = await resp.json()

    return {
        "id": g["id"],
        "name": g["name"],
        "icon": g.get("icon"),
        "iconUrl": _guild_icon_url(g["id"], g.get("icon")),
        "memberCount": g.get("approximate_member_count", 0),
        "description": g.get("description"),
    }


@router.get("/{guild_id}/channels")
async def list_guild_channels(guild_id: str, request: Request):
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return await _fetch_guild_channels(guild_id)


@router.get("/{guild_id}/logs")
async def list_guild_logs(guild_id: str, request: Request):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT id, guild_id, event_type, user_id, target_id, description, metadata, created_at
        FROM log_entries
        WHERE guild_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        guild_id,
    )
    return [
        {
            "id": r["id"],
            "guildId": r["guild_id"],
            "eventType": r["event_type"],
            "userId": r["user_id"],
            "targetId": r["target_id"],
            "description": r["description"],
            "metadata": r["metadata"],
            "createdAt": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/{guild_id}/moderation")
async def list_guild_moderation(guild_id: str, request: Request, userId: Optional[str] = None):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    moderation_event_types = (
        "member_ban", "member_unban", "member_kick",
        "member_timeout_add", "member_timeout_remove", "member_warn",
    )

    if userId:
        rows = await pool.fetch(
            """
            SELECT id, guild_id, event_type, user_id, target_id, description, metadata, created_at
            FROM log_entries
            WHERE guild_id = $1
              AND event_type = ANY($2)
              AND target_id = $3
            ORDER BY created_at DESC
            LIMIT 100
            """,
            guild_id,
            list(moderation_event_types),
            userId,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, guild_id, event_type, user_id, target_id, description, metadata, created_at
            FROM log_entries
            WHERE guild_id = $1
              AND event_type = ANY($2)
            ORDER BY created_at DESC
            LIMIT 100
            """,
            guild_id,
            list(moderation_event_types),
        )

    return [
        {
            "id": r["id"],
            "guildId": r["guild_id"],
            "eventType": r["event_type"],
            "userId": r["user_id"],
            "targetId": r["target_id"],
            "description": r["description"],
            "metadata": r["metadata"],
            "createdAt": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/{guild_id}/warnings/{user_id}")
async def list_user_warnings(guild_id: str, user_id: str, request: Request):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT id, guild_id, event_type, user_id, target_id, description, metadata, created_at
        FROM log_entries
        WHERE guild_id = $1
          AND event_type = 'member_warn'
          AND target_id = $2
        ORDER BY created_at DESC
        """,
        guild_id,
        user_id,
    )
    return [
        {
            "id": r["id"],
            "guildId": r["guild_id"],
            "eventType": r["event_type"],
            "userId": r["user_id"],
            "targetId": r["target_id"],
            "description": r["description"],
            "metadata": r["metadata"],
            "createdAt": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/{guild_id}/leveling-config")
async def get_leveling_config_route(guild_id: str, request: Request):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM leveling_config WHERE guild_id = $1",
        guild_id,
    )
    if row:
        return {
            "guildId": row["guild_id"],
            "textXpMin": row["text_xp_min"],
            "textXpMax": row["text_xp_max"],
            "textXpCooldown": row["text_xp_cooldown"],
            "voiceXpPerMinute": row["voice_xp_per_minute"],
            "levelupChannelId": row["levelup_channel_id"],
            "levelupMessageEnabled": row["levelup_message_enabled"],
        }
    return {
        "guildId": guild_id,
        "textXpMin": 15,
        "textXpMax": 25,
        "textXpCooldown": 60,
        "voiceXpPerMinute": 10,
        "levelupChannelId": None,
        "levelupMessageEnabled": True,
    }


@router.put("/{guild_id}/leveling-config")
async def update_leveling_config_route(guild_id: str, request: Request):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    pool = get_pool()

    await pool.execute(
        """
        INSERT INTO leveling_config (
            guild_id, text_xp_min, text_xp_max, text_xp_cooldown,
            voice_xp_per_minute, levelup_channel_id, levelup_message_enabled, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (guild_id) DO UPDATE SET
            text_xp_min             = EXCLUDED.text_xp_min,
            text_xp_max             = EXCLUDED.text_xp_max,
            text_xp_cooldown        = EXCLUDED.text_xp_cooldown,
            voice_xp_per_minute     = EXCLUDED.voice_xp_per_minute,
            levelup_channel_id      = EXCLUDED.levelup_channel_id,
            levelup_message_enabled = EXCLUDED.levelup_message_enabled,
            updated_at              = NOW()
        """,
        guild_id,
        body.get("textXpMin", 15),
        body.get("textXpMax", 25),
        body.get("textXpCooldown", 60),
        body.get("voiceXpPerMinute", 10),
        body.get("levelupChannelId"),
        body.get("levelupMessageEnabled", True),
    )

    return {
        "guildId": guild_id,
        "textXpMin": body.get("textXpMin", 15),
        "textXpMax": body.get("textXpMax", 25),
        "textXpCooldown": body.get("textXpCooldown", 60),
        "voiceXpPerMinute": body.get("voiceXpPerMinute", 10),
        "levelupChannelId": body.get("levelupChannelId"),
        "levelupMessageEnabled": body.get("levelupMessageEnabled", True),
    }


@router.get("/{guild_id}/leaderboard")
async def get_leaderboard_route(guild_id: str, request: Request, category: str = "text"):
    from web.core.database import get_pool
    session = _require_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()

    if category == "voice":
        rows = await pool.fetch(
            """
            SELECT user_id, voice_xp AS xp, voice_level AS level
            FROM member_xp
            WHERE guild_id = $1
            ORDER BY voice_xp DESC
            LIMIT 10
            """,
            guild_id,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT user_id, text_xp AS xp, text_level AS level
            FROM member_xp
            WHERE guild_id = $1
            ORDER BY text_xp DESC
            LIMIT 10
            """,
            guild_id,
        )

    return [
        {"userId": r["user_id"], "xp": r["xp"], "level": r["level"], "rank": i + 1}
        for i, r in enumerate(rows)
    ]
