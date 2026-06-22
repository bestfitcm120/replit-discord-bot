import asyncio
import discord
from typing import Optional, Union


async def get_audit_executor(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    target_id: Optional[int] = None,
    max_age: float = 5.0,
    delay: float = 0.6,
) -> Optional[Union[discord.Member, discord.User]]:
    """
    Fetch the executor (who performed an action) from the audit log.
    Returns None if not found, audit log is unavailable, or the bot lacks permission.
    """
    await asyncio.sleep(delay)
    try:
        async for entry in guild.audit_logs(limit=6, action=action):
            age = (discord.utils.utcnow() - entry.created_at).total_seconds()
            if age > max_age:
                break
            if target_id is None:
                return entry.user
            if hasattr(entry.target, "id") and entry.target.id == target_id:
                return entry.user
    except (discord.Forbidden, discord.HTTPException):
        pass
    return None


def executor_field(executor: Optional[Union[discord.Member, discord.User]]) -> str:
    """Format an executor mention for embed fields."""
    if executor:
        return f"{executor.mention} (`{executor}`)"
    return "*Unknown (no audit log access)*"
