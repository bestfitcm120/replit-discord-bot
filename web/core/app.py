from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from web.core.config import WebConfig
from web.core.database import lifespan
from web.features.auth.router import router as auth_router
from web.features.guilds.router import router as guilds_router
from web.features.config.router import router as config_router
from web.features.stats.router import router as stats_router


def create_app() -> FastAPI:
    config = WebConfig.from_env()

    app = FastAPI(
        title="Discord Moderation Bot — Admin API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(guilds_router, prefix="/api/guilds", tags=["guilds"])
    app.include_router(config_router, prefix="/api/guilds", tags=["config"])
    app.include_router(stats_router, prefix="/api/guilds", tags=["stats"])

    # Health check
    @app.get("/api/healthz")
    async def health_check():
        return {"status": "ok"}

    # Bot invite URL
    @app.get("/api/bot/invite")
    async def bot_invite():
        permissions = int(os.environ.get("DISCORD_BOT_PERMISSIONS", "8"))
        client_id = os.environ.get("DISCORD_CLIENT_ID", "")
        url = (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={client_id}"
            f"&permissions={permissions}"
            f"&scope=bot%20applications.commands"
        )
        return {"url": url}

    # Serve React static files if they exist
    static_dir = os.path.join(os.path.dirname(__file__), "../../dist")
    if os.path.isdir(static_dir):
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            index_file = os.path.join(static_dir, "index.html")
            return FileResponse(index_file)

    return app
