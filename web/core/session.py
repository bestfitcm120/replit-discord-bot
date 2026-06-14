"""
Lightweight signed-cookie session using itsdangerous.
"""
from itsdangerous import URLSafeTimedSerializer
from fastapi import Request, Response
import os
from typing import Optional, Dict, Any

_serializer: Optional[URLSafeTimedSerializer] = None
COOKIE_NAME = "modbot_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        secret = os.environ.get("SESSION_SECRET", "change-me")
        _serializer = URLSafeTimedSerializer(secret)
    return _serializer


def set_session(response: Response, data: Dict[str, Any]) -> None:
    s = _get_serializer()
    token = s.dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("SECURE_COOKIES", "").lower() == "true",
    )


def get_session(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        s = _get_serializer()
        return s.loads(token, max_age=MAX_AGE)
    except Exception:
        return None


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
