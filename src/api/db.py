# App-level tables (session registry + upload metadata).
# Conversation history/state itself is persisted by ADK's DatabaseSessionService.
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

_engine: AsyncEngine | None = None

DDL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE app_sessions ADD COLUMN IF NOT EXISTS user_id TEXT;
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES app_sessions(id),
    filename TEXT NOT NULL,
    s3_key TEXT,
    status TEXT NOT NULL DEFAULT 'received',
    row_count INTEGER,
    columns TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS fivetran_credentials (
    user_id TEXT PRIMARY KEY,
    api_key_enc TEXT NOT NULL,
    api_secret_enc TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("Missing DATABASE_URL in .env")
    # Neon gives postgresql:// — SQLAlchemy async needs the asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # asyncpg doesn't understand libpq-style query params Neon appends
    base, _, query = url.partition("?")
    if query:
        unsupported = ("sslmode=", "channel_binding=", "options=")
        params = [p for p in query.split("&")
                  if p and not p.startswith(unsupported)]
        url = base + ("?" + "&".join(params) if params else "")
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # Neon requires SSL; pass it natively since we stripped sslmode from the URL
        _engine = create_async_engine(
            get_db_url(), pool_pre_ping=True, connect_args={"ssl": True}
        )
    return _engine


async def init_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for stmt in DDL.strip().split(";"):
            if stmt.strip():
                await conn.execute(text(stmt))
