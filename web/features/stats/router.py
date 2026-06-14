from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta

from web.core.database import get_pool
from web.core.session import get_session

router = APIRouter()


@router.get("/{guild_id}/stats")
async def get_guild_stats(guild_id: str, request: Request):
    session = get_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    joins_row = await pool.fetchrow(
        "SELECT COUNT(*) AS cnt FROM member_events WHERE guild_id = $1 AND event_type = 'join' AND created_at >= $2",
        guild_id, since_24h,
    )
    leaves_row = await pool.fetchrow(
        "SELECT COUNT(*) AS cnt FROM member_events WHERE guild_id = $1 AND event_type = 'leave' AND created_at >= $2",
        guild_id, since_24h,
    )
    messages_row = await pool.fetchrow(
        """
        SELECT COALESCE(SUM(count), 0) AS cnt
        FROM message_stats
        WHERE guild_id = $1 AND is_bot = FALSE AND stat_date >= $2::date
        """,
        guild_id, since_24h.date(),
    )

    # Approximate total from member events
    total_joins = await pool.fetchrow(
        "SELECT COUNT(*) AS cnt FROM member_events WHERE guild_id = $1 AND event_type = 'join'", guild_id,
    )
    total_leaves = await pool.fetchrow(
        "SELECT COUNT(*) AS cnt FROM member_events WHERE guild_id = $1 AND event_type = 'leave'", guild_id,
    )
    total_members = max(0, (total_joins["cnt"] or 0) - (total_leaves["cnt"] or 0))

    return {
        "guildId": guild_id,
        "totalMembers": total_members,
        "membersJoinedLast24h": joins_row["cnt"] or 0,
        "membersLeftLast24h": leaves_row["cnt"] or 0,
        "messagesLast24h": messages_row["cnt"] or 0,
        "onlineMembers": None,
    }


@router.get("/{guild_id}/stats/members")
async def get_guild_member_history(guild_id: str, request: Request):
    session = get_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    since = datetime.now(timezone.utc) - timedelta(days=30)

    rows = await pool.fetch(
        """
        SELECT
            DATE(created_at) AS date,
            COUNT(*) FILTER (WHERE event_type = 'join')  AS joins,
            COUNT(*) FILTER (WHERE event_type = 'leave') AS leaves
        FROM member_events
        WHERE guild_id = $1 AND created_at >= $2
        GROUP BY DATE(created_at)
        ORDER BY date
        """,
        guild_id, since,
    )

    running_total = 0
    result = []
    for r in rows:
        running_total += r["joins"] - r["leaves"]
        result.append({
            "date": r["date"].isoformat(),
            "joins": r["joins"],
            "leaves": r["leaves"],
            "total": max(0, running_total),
        })
    return result


@router.get("/{guild_id}/stats/messages")
async def get_guild_message_history(guild_id: str, request: Request):
    session = get_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    pool = get_pool()
    since = datetime.now(timezone.utc) - timedelta(days=7)

    rows = await pool.fetch(
        """
        SELECT stat_date AS date, COALESCE(SUM(count), 0) AS count
        FROM message_stats
        WHERE guild_id = $1 AND is_bot = FALSE AND stat_date >= $2::date
        GROUP BY stat_date
        ORDER BY stat_date
        """,
        guild_id, since.date(),
    )

    return [
        {"date": r["date"].isoformat(), "count": int(r["count"])}
        for r in rows
    ]
