"""
Discord OAuth2 authentication routes.

Flow:
  GET /api/auth/discord          → redirect to Discord
  GET /api/auth/discord/callback → exchange code, set session, redirect to /servers
  GET /api/auth/me               → return current user or 401
  POST /api/auth/logout          → clear session
"""
import os
import aiohttp
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse

from web.core.session import get_session, set_session, clear_session

router = APIRouter()

DISCORD_API = "https://discord.com/api/v10"
OAUTH_SCOPES = "identify guilds"


def _oauth_url() -> str:
    client_id = os.environ.get("DISCORD_CLIENT_ID", "")
    redirect_uri = _redirect_uri()
    scopes = OAUTH_SCOPES.replace(" ", "%20")
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
    )


def _redirect_uri() -> str:
    base = os.environ.get("BASE_URL", "http://localhost:8000")
    return f"{base}/api/auth/discord/callback"


@router.get("/discord")
async def discord_login():
    return RedirectResponse(_oauth_url())


@router.get("/discord/callback")
async def discord_callback(code: str, request: Request):
    token_data = await _exchange_code(code)
    if not token_data or "access_token" not in token_data:
        return RedirectResponse("/?error=oauth_failed")

    access_token = token_data["access_token"]
    user = await _fetch_discord_user(access_token)
    if not user:
        return RedirectResponse("/?error=user_fetch_failed")

    session_data = {
        "user_id": user["id"],
        "username": user["username"],
        "discriminator": user.get("discriminator", "0"),
        "avatar": user.get("avatar"),
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
    }

    response = RedirectResponse("/servers")
    set_session(response, session_data)
    return response


@router.get("/me")
async def get_me(request: Request):
    session = get_session(request)
    if not session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    avatar_hash = session.get("avatar")
    user_id = session["user_id"]
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
        if avatar_hash
        else f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"
    )

    return {
        "id": user_id,
        "username": session["username"],
        "discriminator": session.get("discriminator", "0"),
        "avatar": avatar_hash,
        "avatarUrl": avatar_url,
    }


@router.post("/logout")
async def logout(response: Response):
    clear_session(response)
    return {"message": "Logged out"}


async def _exchange_code(code: str) -> dict:
    client_id = os.environ.get("DISCORD_CLIENT_ID", "")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "")
    redirect_uri = _redirect_uri()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            return await resp.json()


async def _fetch_discord_user(access_token: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            return await resp.json()
