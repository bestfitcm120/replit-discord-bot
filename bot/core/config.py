import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    token: str
    prefix: str
    database_url: str
    web_api_url: str

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable is required")

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        return cls(
            token=token,
            prefix=os.environ.get("BOT_PREFIX", "!"),
            database_url=database_url,
            web_api_url=os.environ.get("WEB_API_URL", "http://web:8000"),
        )
