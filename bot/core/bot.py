import discord
from discord.ext import commands
import logging
import os

from bot.core.config import BotConfig

logger = logging.getLogger(__name__)


class ModerationBot(commands.Bot):
    def __init__(self, config: BotConfig):
        self.config = config
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.moderation = True
        intents.invites = True

        super().__init__(
            command_prefix=config.prefix,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await self._load_features()
        await self.tree.sync()
        logger.info("Bot setup complete, commands synced.")

    async def _load_features(self) -> None:
        extensions = [
            "bot.features.logging.cog",
            "bot.features.moderation.cog",
            "bot.features.temp_voice.cog",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers",
            )
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
