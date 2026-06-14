import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class WebConfig:
    database_url: str
    discord_client_id: str
    discord_client_secret: str
    discord_bot_token: str
    session_secret: str
    base_url: str
    cors_origins: List[str]
    bot_permissions: int

    @classmethod
    def from_env(cls) -> "WebConfig":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is required")

        client_id = os.environ.get("DISCORD_CLIENT_ID")
        if not client_id:
            raise ValueError("DISCORD_CLIENT_ID is required")

        client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
        if not client_secret:
            raise ValueError("DISCORD_CLIENT_SECRET is required")

        bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        if not bot_token:
            raise ValueError("DISCORD_BOT_TOKEN is required")

        session_secret = os.environ.get("SESSION_SECRET", "change-me-in-production")
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")

        cors_raw = os.environ.get("CORS_ORIGINS", base_url)
        cors_origins = [o.strip() for o in cors_raw.split(",")]

        return cls(
            database_url=database_url,
            discord_client_id=client_id,
            discord_client_secret=client_secret,
            discord_bot_token=bot_token,
            session_secret=session_secret,
            base_url=base_url,
            cors_origins=cors_origins,
            bot_permissions=int(os.environ.get("DISCORD_BOT_PERMISSIONS", "8")),
        )
