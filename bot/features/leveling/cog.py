import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import random
import datetime
from typing import Optional

from bot.core.database import (
    get_pool,
    add_text_xp,
    add_voice_xp,
    get_user_xp,
    get_user_text_rank,
    get_user_voice_rank,
    get_text_leaderboard,
    get_voice_leaderboard,
    get_leveling_config,
    xp_for_level,
)

logger = logging.getLogger(__name__)


class LevelingCog(commands.Cog, name="Leveling"):
    """
    XP and leveling system.
    Members earn XP by sending messages (text XP, with cooldown) and by
    being in voice channels (voice XP, awarded per minute).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool = None
        # Track voice join times: {guild_id: {user_id: datetime}}
        self._voice_sessions: dict[str, dict[str, datetime.datetime]] = {}

    async def cog_load(self) -> None:
        self.pool = await get_pool(self.bot.config.database_url)
        self._voice_xp_tick.start()
        logger.info("LevelingCog loaded.")

    async def cog_unload(self) -> None:
        self._voice_xp_tick.cancel()

    # ──────────────────────────────────────────────────────────────────────
    # Voice session tracking
    # ──────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        guild_id = str(member.guild.id)
        user_id = str(member.id)
        now = datetime.datetime.now(datetime.timezone.utc)

        if guild_id not in self._voice_sessions:
            self._voice_sessions[guild_id] = {}

        # User joined a voice channel
        if not before.channel and after.channel:
            self._voice_sessions[guild_id][user_id] = now

        # User left a voice channel
        elif before.channel and not after.channel:
            await self._award_voice_xp(member, guild_id, user_id, now)

        # User moved between channels — reset timer
        elif before.channel and after.channel and before.channel != after.channel:
            await self._award_voice_xp(member, guild_id, user_id, now)
            self._voice_sessions[guild_id][user_id] = now

    async def _award_voice_xp(
        self,
        member: discord.Member,
        guild_id: str,
        user_id: str,
        now: datetime.datetime,
    ) -> None:
        sessions = self._voice_sessions.get(guild_id, {})
        joined_at = sessions.pop(user_id, None)
        if joined_at is None:
            return

        config = await get_leveling_config(self.pool, guild_id)
        xp_per_minute = config.get("voice_xp_per_minute", 10)
        elapsed_minutes = max(0, (now - joined_at).total_seconds() / 60)
        if elapsed_minutes < 1:
            return

        xp = int(elapsed_minutes * xp_per_minute)
        result = await add_voice_xp(self.pool, guild_id, user_id, xp)

        if result and result["new_level"] > result["old_level"]:
            await self._send_levelup(member, "Voice", result["new_level"], config)

    @tasks.loop(minutes=1)
    async def _voice_xp_tick(self) -> None:
        """Award incremental voice XP every minute for all users currently in voice."""
        now = datetime.datetime.now(datetime.timezone.utc)
        for guild_id, sessions in list(self._voice_sessions.items()):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            config = await get_leveling_config(self.pool, guild_id)
            xp_per_minute = config.get("voice_xp_per_minute", 10)

            for user_id, joined_at in list(sessions.items()):
                member = guild.get_member(int(user_id))
                if not member or not member.voice or not member.voice.channel:
                    sessions.pop(user_id, None)
                    continue

                result = await add_voice_xp(self.pool, guild_id, user_id, xp_per_minute)
                if result and result["new_level"] > result["old_level"]:
                    await self._send_levelup(member, "Voice", result["new_level"], config)
                sessions[user_id] = now

    @_voice_xp_tick.before_loop
    async def before_voice_xp_tick(self):
        await self.bot.wait_until_ready()

    # ──────────────────────────────────────────────────────────────────────
    # Text XP
    # ──────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        config = await get_leveling_config(self.pool, guild_id)
        xp_min = config.get("text_xp_min", 15)
        xp_max = config.get("text_xp_max", 25)
        cooldown = config.get("text_xp_cooldown", 60)
        xp = random.randint(xp_min, xp_max)

        result = await add_text_xp(self.pool, guild_id, user_id, xp, cooldown)
        if result and result["new_level"] > result["old_level"]:
            await self._send_levelup(message.author, "Text", result["new_level"], config)

    # ──────────────────────────────────────────────────────────────────────
    # Level-up celebration
    # ──────────────────────────────────────────────────────────────────────

    async def _send_levelup(
        self,
        member: discord.Member,
        category: str,
        new_level: int,
        config: dict,
    ) -> None:
        if not config.get("levelup_message_enabled", True):
            return
        channel_id = config.get("levelup_channel_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title="🎉 Level Up!",
            description=(
                f"Congratulations {member.mention}! You've reached **Level {new_level}** in **{category}**!"
            ),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Keep it up! Next level at {xp_for_level(new_level + 1)} XP")
        try:
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ──────────────────────────────────────────────────────────────────────
    # Slash commands
    # ──────────────────────────────────────────────────────────────────────

    @app_commands.command(name="rank", description="Show your rank and level, or that of another member.")
    @app_commands.describe(member="The member to check (leave blank for yourself)")
    async def rank_command(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
    ) -> None:
        target = member or interaction.user
        guild_id = str(interaction.guild_id)
        user_id = str(target.id)

        xp_data = await get_user_xp(self.pool, guild_id, user_id)
        text_rank = await get_user_text_rank(self.pool, guild_id, user_id)
        voice_rank = await get_user_voice_rank(self.pool, guild_id, user_id)

        text_xp = xp_data["text_xp"]
        voice_xp = xp_data["voice_xp"]
        text_level = xp_data["text_level"]
        voice_level = xp_data["voice_level"]

        text_next = xp_for_level(text_level + 1)
        voice_next = xp_for_level(voice_level + 1)

        embed = discord.Embed(
            title=f"Rank — {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name="💬 Text",
            value=(
                f"**Level:** {text_level}\n"
                f"**XP:** {text_xp:,} / {text_next:,}\n"
                f"**Rank:** #{text_rank}"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔊 Voice",
            value=(
                f"**Level:** {voice_level}\n"
                f"**XP:** {voice_xp:,} / {voice_next:,}\n"
                f"**Rank:** #{voice_rank}"
            ),
            inline=True,
        )
        embed.set_footer(text=f"User ID: {target.id}")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="Show the top 5 text and voice chatters in this server.")
    async def top_command(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        guild_id = str(guild.id)

        text_rows = await get_text_leaderboard(self.pool, guild_id, limit=5)
        voice_rows = await get_voice_leaderboard(self.pool, guild_id, limit=5)

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

        def format_rows(rows: list, xp_key: str, level_key: str) -> str:
            if not rows:
                return "*No data yet.*"
            lines = []
            for i, row in enumerate(rows):
                medal = medals[i] if i < len(medals) else f"**#{i + 1}**"
                lines.append(f"{medal} <@{row['user_id']}>\nLvl **{row[level_key]}** • {row[xp_key]:,} XP")
            return "\n".join(lines)

        embed = discord.Embed(
            title=f"🏆 {guild.name} Leaderboard",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="💬 Top Text Chatters",
            value=format_rows(text_rows, "text_xp", "text_level"),
            inline=True,
        )
        embed.add_field(
            name="🔊 Top Voice Members",
            value=format_rows(voice_rows, "voice_xp", "voice_level"),
            inline=True,
        )
        embed.set_footer(text="Use /rank to see your own stats")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LevelingCog(bot))
