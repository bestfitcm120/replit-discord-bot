"""
Admin Dashboard — FastAPI web server entry point.

Environment variables required:
  DATABASE_URL          — PostgreSQL connection string
  DISCORD_CLIENT_ID     — your Discord application client ID
  DISCORD_CLIENT_SECRET — your Discord application client secret
  DISCORD_BOT_TOKEN     — bot token (for fetching guild data)
  SESSION_SECRET        — secret key for signing session cookies
  BASE_URL              — public base URL, e.g. https://yourdomain.com
  DISCORD_BOT_PERMISSIONS — integer permissions (default: 8 for admin)
"""
import uvicorn
import os

from web.core.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "web.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
