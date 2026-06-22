import asyncio
import discord
from typing import List, Tuple, Optional

from bot.utils.audit import get_audit_executor, executor_field


class VoiceEventHandlers:
    @staticmethod
    async def voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> List[Tuple[discord.Embed, str]]:
        results: List[Tuple[discord.Embed, str]] = []
        guild = member.guild

        # Member moved from one channel to another
        if before.channel and after.channel and before.channel != after.channel:
            executor = await get_audit_executor(
                guild,
                discord.AuditLogAction.member_move,
                target_id=None,
                max_age=5.0,
            )

            if executor and executor.id != member.id:
                description = (
                    f"{member.mention} was moved from **{before.channel.name}** to **{after.channel.name}** "
                    f"by {executor.mention} (`{executor}`)."
                )
                title = "Member Moved Voice Channel (by Admin)"
            else:
                description = (
                    f"{member.mention} moved from **{before.channel.name}** to **{after.channel.name}**."
                )
                title = "Member Moved Voice Channel"

            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue(),
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()
            results.append((embed, "member_voice_move"))

        # Member disconnected from voice
        elif before.channel and not after.channel:
            executor = await get_audit_executor(
                guild,
                discord.AuditLogAction.member_disconnect,
                target_id=None,
                max_age=5.0,
            )

            if executor and executor.id != member.id:
                description = (
                    f"{member.mention} was disconnected from **{before.channel.name}** "
                    f"by {executor.mention} (`{executor}`)."
                )
                title = "Member Disconnected from Voice (by Admin)"
            else:
                description = (
                    f"{member.mention} disconnected from **{before.channel.name}**."
                )
                title = "Member Disconnected from Voice"

            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.dark_red(),
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()
            results.append((embed, "member_voice_disconnect"))

        return results
