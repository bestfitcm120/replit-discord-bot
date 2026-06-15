"""
Moderation slash commands: /ban, /unban, /kick, /timeout, /untimeout, /purge, /warn
Each action is logged to the database and dispatched to the configured log channel.
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import timedelta
from typing import Optional

from bot.core.database import get_pool, get_log_channel, insert_log_entry

logger = logging.getLogger(__name__)

MOD_COLOR = discord.Color.red()
GOOD_COLOR = discord.Color.green()
WARN_COLOR = discord.Color.orange()


def _user_line(user: discord.User | discord.Member) -> str:
    return f"{user.mention} (`{user}` • ID: {user.id})"


async def _try_dm(user: discord.User | discord.Member, embed: discord.Embed) -> None:
    try:
        await user.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


class ModerationCog(commands.Cog, name="Moderation"):
    """Slash-command moderation tools."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = None

    async def cog_load(self) -> None:
        self.pool = await get_pool(self.bot.config.database_url)
        logger.info("ModerationCog loaded.")

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _log(
        self,
        guild: discord.Guild,
        event_type: str,
        embed: discord.Embed,
        *,
        moderator_id: Optional[str] = None,
        target_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        channel_id = await get_log_channel(self.pool, str(guild.id), event_type)
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(embed=embed)
                except (discord.Forbidden, discord.HTTPException) as exc:
                    logger.warning(f"Could not send log to {channel_id}: {exc}")

        await insert_log_entry(
            self.pool,
            guild_id=str(guild.id),
            event_type=event_type,
            description=embed.description or "",
            user_id=moderator_id,
            target_id=target_id,
            metadata=metadata or {},
        )

    def _mod_footer(self, interaction: discord.Interaction) -> str:
        return f"Moderator: {interaction.user} (ID: {interaction.user.id})"

    # ──────────────────────────────────────────────────────────────────────────
    # /ban
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for the ban",
        delete_days="Days of messages to delete (0–7)",
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None,
        delete_days: Optional[app_commands.Range[int, 0, 7]] = 0,
    ) -> None:
        reason_text = reason or "No reason provided"
        guild = interaction.guild

        dm_embed = discord.Embed(
            title=f"You have been banned from {guild.name}",
            description=f"**Reason:** {reason_text}",
            color=MOD_COLOR,
        )
        await _try_dm(member, dm_embed)

        await guild.ban(member, reason=f"{interaction.user}: {reason_text}", delete_message_days=delete_days or 0)

        log_embed = discord.Embed(
            title="Member Banned",
            description=f"{_user_line(member)} was banned.",
            color=MOD_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason_text, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_ban", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id),
            metadata={"reason": reason_text, "delete_days": delete_days},
        )

        await interaction.response.send_message(
            f"✅ **{member}** has been banned. Reason: {reason_text}", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /unban
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="unban", description="Unban a user by their Discord ID.")
    @app_commands.describe(user_id="The Discord user ID to unban", reason="Reason for unbanning")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        reason_text = reason or "No reason provided"

        try:
            uid = int(user_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
            return

        try:
            ban_entry = await guild.fetch_ban(discord.Object(id=uid))
        except discord.NotFound:
            await interaction.response.send_message("❌ That user is not banned.", ephemeral=True)
            return

        user = ban_entry.user
        await guild.unban(user, reason=f"{interaction.user}: {reason_text}")

        log_embed = discord.Embed(
            title="Member Unbanned",
            description=f"{_user_line(user)} was unbanned.",
            color=GOOD_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason_text, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_unban", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(user.id),
            metadata={"reason": reason_text},
        )

        await interaction.response.send_message(
            f"✅ **{user}** has been unbanned.", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /kick
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        reason_text = reason or "No reason provided"

        dm_embed = discord.Embed(
            title=f"You have been kicked from {guild.name}",
            description=f"**Reason:** {reason_text}",
            color=MOD_COLOR,
        )
        await _try_dm(member, dm_embed)

        await member.kick(reason=f"{interaction.user}: {reason_text}")

        log_embed = discord.Embed(
            title="Member Kicked",
            description=f"{_user_line(member)} was kicked.",
            color=MOD_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason_text, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_kick", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id),
            metadata={"reason": reason_text},
        )

        await interaction.response.send_message(
            f"✅ **{member}** has been kicked. Reason: {reason_text}", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /timeout
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="timeout", description="Timeout a member (mute) for a duration.")
    @app_commands.describe(
        member="The member to timeout",
        minutes="Duration in minutes (1–40320 / 28 days)",
        reason="Reason for the timeout",
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        reason_text = reason or "No reason provided"
        duration = timedelta(minutes=minutes)

        dm_embed = discord.Embed(
            title=f"You have been timed out in {guild.name}",
            description=f"**Duration:** {minutes} minute(s)\n**Reason:** {reason_text}",
            color=WARN_COLOR,
        )
        await _try_dm(member, dm_embed)

        await member.timeout(duration, reason=f"{interaction.user}: {reason_text}")

        log_embed = discord.Embed(
            title="Member Timed Out",
            description=f"{_user_line(member)} was timed out for **{minutes}** minute(s).",
            color=WARN_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason_text, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_timeout_add", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id),
            metadata={"reason": reason_text, "minutes": minutes},
        )

        await interaction.response.send_message(
            f"✅ **{member}** has been timed out for {minutes} minute(s).", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /untimeout
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="untimeout", description="Remove an active timeout from a member.")
    @app_commands.describe(member="The member to remove the timeout from", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[str] = None,
    ) -> None:
        guild = interaction.guild
        reason_text = reason or "No reason provided"

        if not member.is_timed_out():
            await interaction.response.send_message("❌ That member is not currently timed out.", ephemeral=True)
            return

        await member.timeout(None, reason=f"{interaction.user}: {reason_text}")

        log_embed = discord.Embed(
            title="Timeout Removed",
            description=f"Timeout removed from {_user_line(member)}.",
            color=GOOD_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason_text, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_timeout_remove", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id),
            metadata={"reason": reason_text},
        )

        await interaction.response.send_message(
            f"✅ Timeout removed from **{member}**.", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /warn
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="warn", description="Issue a formal warning to a member.")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        guild = interaction.guild

        dm_embed = discord.Embed(
            title=f"Warning in {guild.name}",
            description=f"You have received a formal warning.\n**Reason:** {reason}",
            color=WARN_COLOR,
        )
        await _try_dm(member, dm_embed)

        log_embed = discord.Embed(
            title="Member Warned",
            description=f"{_user_line(member)} was warned.",
            color=WARN_COLOR,
        )
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            guild, "member_warn", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id),
            metadata={"reason": reason},
        )

        await interaction.response.send_message(
            f"⚠️ **{member}** has been warned. Reason: {reason}", ephemeral=True
        )

    # ──────────────────────────────────────────────────────────────────────────
    # /purge
    # ──────────────────────────────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Bulk delete messages from a channel.")
    @app_commands.describe(
        count="Number of messages to delete (1–100)",
        member="Only delete messages from this member (optional)",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 100],
        member: Optional[discord.Member] = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        def check(m: discord.Message) -> bool:
            return member is None or m.author == member

        deleted = await channel.purge(limit=count, check=check)

        log_embed = discord.Embed(
            title="Messages Purged",
            description=f"**{len(deleted)}** message(s) deleted in {channel.mention}."
            + (f" (filtered to {member.mention})" if member else ""),
            color=MOD_COLOR,
        )
        log_embed.set_footer(text=self._mod_footer(interaction))

        await self._log(
            interaction.guild, "message_delete", log_embed,
            moderator_id=str(interaction.user.id),
            target_id=str(member.id) if member else None,
            metadata={
                "purge": True,
                "count": len(deleted),
                "channel": channel.name,
                "filter_user": str(member) if member else None,
            },
        )

        await interaction.followup.send(
            f"✅ Deleted **{len(deleted)}** message(s).", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))
