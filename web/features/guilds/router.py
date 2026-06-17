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
            # Return only text channels (type 0), voice channels (type 2) and announcement channels (type 5)
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

    # Filter to guilds where the user has MANAGE_GUILD (0x20)
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
