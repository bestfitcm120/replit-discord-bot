"""
Temporary Voice Channel feature.

When a member joins the configured "creation" voice channel:
  1. A new temporary voice channel is created (inheriting the creation channel's
     permission overwrites, bitrate, and user limit).
  2. The owner gets an additional user-level overwrite granting full control.
  3. The member is moved to the new channel.
  4. When the last member leaves, the channel is automatically deleted.

On bot startup, stale entries in the DB (channels that no longer exist in Discord,
or are already empty) are cleaned up automatically.
"""
import discord
from discord.ext import commands
import logging
from typing import Optional

from bot.core.database import (
    get_pool,
    get_creation_voice_channel,
    add_temp_channel,
    remove_temp_channel,
    is_temp_channel,
    get_all_temp_channels,
)

logger = logging.getLogger(__name__)

# Full set of permissions granted to the channel owner.
OWNER_PERMISSIONS = discord.PermissionOverwrite(
    connect=True,
    speak=True,
    stream=True,
    use_voice_activation=True,
    use_soundboard=True,
    use_embedded_activities=True,
    priority_speaker=True,
    manage_channels=True,
    move_members=True,
    deafen_members=True,
    mute_members=True,
)


class TempVoiceCog(commands.Cog, name="TempVoice"):
    """Creates and manages temporary voice channels."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = None

    async def cog_load(self) -> None:
        self.pool = await get_pool(self.bot.config.database_url)
        await self._startup_cleanup()
        logger.info("TempVoiceCog loaded.")

    # ──────────────────────────────────────────────────────────────────────────
    # Startup cleanup
    # ──────────────────────────────────────────────────────────────────────────

    async def _startup_cleanup(self) -> None:
        """
        On restart, remove DB entries for channels that no longer exist in
        Discord, and delete any tracked channels that are now empty.
        """
        rows = await get_all_temp_channels(self.pool)
        for row in rows:
            guild = self.bot.get_guild(int(row["guild_id"]))
            if guild is None:
                # Guild not cached yet — skip (will be handled when the guild becomes available)
                continue

            channel = guild.get_channel(int(row["channel_id"]))
            if channel is None:
                # Channel was deleted while bot was offline
                await remove_temp_channel(self.pool, row["channel_id"])
                logger.info(f"Cleaned up missing temp channel {row['channel_id']}")
            elif isinstance(channel, discord.VoiceChannel) and len(channel.members) == 0:
                # Channel exists but is empty — delete it
                try:
                    await channel.delete(reason="Temp voice cleanup on bot restart")
                except (discord.Forbidden, discord.HTTPException):
                    pass
                await remove_temp_channel(self.pool, row["channel_id"])
                logger.info(f"Deleted empty temp channel {row['channel_id']} on startup")

    # ──────────────────────────────────────────────────────────────────────────
    # Voice state listener
    # ──────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild_id = str(member.guild.id)

        # ── User joined a channel ─────────────────────────────────────────────
        if after.channel is not None and after.channel != before.channel:
            creation_id = await get_creation_voice_channel(self.pool, guild_id)
            if creation_id and str(after.channel.id) == creation_id:
                # Don't treat the creation channel itself as a temp channel
                if not await is_temp_channel(self.pool, str(after.channel.id)):
                    await self._create_temp_channel(member, after.channel)

        # ── User left a channel ───────────────────────────────────────────────
        if before.channel is not None and before.channel != after.channel:
            if await is_temp_channel(self.pool, str(before.channel.id)):
                # Re-fetch the channel to get the current member list
                channel = member.guild.get_channel(before.channel.id)
                if channel is None or len(channel.members) == 0:
                    await self._delete_temp_channel(before.channel)

    # ──────────────────────────────────────────────────────────────────────────
    # Channel creation / deletion helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _create_temp_channel(
        self,
        member: discord.Member,
        creation_channel: discord.VoiceChannel,
    ) -> Optional[discord.VoiceChannel]:
        guild = member.guild

        # Copy ALL permission overwrites from the creation channel so the
        # admin's existing Discord permission setup is fully preserved.
        overwrites: dict = dict(creation_channel.overwrites)

        # Add an owner-specific overwrite on top. Because Discord resolves
        # user overwrites after role overwrites, this grants the owner full
        # control without affecting anyone else's permissions.
        overwrites[member] = OWNER_PERMISSIONS

        channel_name = f"⌛ {member.display_name}"

        try:
            temp_channel = await guild.create_voice_channel(
                name=channel_name,
                category=creation_channel.category,
                overwrites=overwrites,
                bitrate=creation_channel.bitrate,
                user_limit=creation_channel.user_limit,
                reason=f"Temp voice for {member} ({member.id})",
            )
        except discord.Forbidden:
            logger.warning(
                f"Missing permissions to create voice channel in guild {guild.id}"
            )
            return None
        except discord.HTTPException as exc:
            logger.error(f"Failed to create temp voice channel: {exc}")
            return None

        # Move the member into the new channel
        try:
            await member.move_to(temp_channel, reason="Moving to temp voice channel")
        except discord.HTTPException as exc:
            logger.warning(f"Could not move {member} to temp channel: {exc}")
            # Still track it so it gets cleaned up when empty
        
        await add_temp_channel(self.pool, str(temp_channel.id), str(guild.id), str(member.id))
        logger.info(
            f"Created temp voice channel '{channel_name}' ({temp_channel.id}) "
            f"for {member} in guild {guild.id}"
        )
        return temp_channel

    async def _delete_temp_channel(self, channel: discord.VoiceChannel) -> None:
        channel_id = str(channel.id)
        try:
            await channel.delete(reason="Temp voice channel — all members left")
            logger.info(f"Deleted empty temp voice channel {channel_id}")
        except discord.NotFound:
            pass  # Already gone
        except (discord.Forbidden, discord.HTTPException) as exc:
            logger.warning(f"Could not delete temp channel {channel_id}: {exc}")
        finally:
            await remove_temp_channel(self.pool, channel_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoiceCog(bot))
