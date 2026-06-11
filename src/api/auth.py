# Authentication: bcrypt password hashing + JWT bearer tokens.
import os
import time

import bcrypt
import jwt
from fastapi import Header, HTTPException
from sqlalchemy import text

JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


# --- passwords -------------------------------------------------------------
def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; truncate to stay within that limit.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


# --- tokens ----------------------------------------------------------------
def make_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


# FastAPI dependency: returns the authenticated user's id, or 401.
async def get_current_user(authorization: str = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


# Shared ownership guard so users can only touch their own sessions.
async def assert_session_owner(session_id: str, user_id: str) -> None:
    from .db import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT 1 FROM app_sessions WHERE id = :sid AND user_id = :uid"),
                {"sid": session_id, "uid": user_id},
            )
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
