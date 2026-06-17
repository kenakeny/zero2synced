# FastAPI entrypoint. Agents are created per-user from each user's stored
# Fivetran keys (see agent_pool), so we do NOT build a shared agent at startup.
import asyncio
import json
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Bootstrap Vertex AI service account credentials from env var.
# Must happen before any google-auth import so ADC resolution picks it up.
_sa_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip().lstrip("﻿")
if _sa_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    try:
        _tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        _tf.write(_sa_json)
        _tf.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tf.name
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.adk.sessions import DatabaseSessionService
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

from .db import init_tables, get_db_url  # noqa: E402
from .routes import chat, sessions, uploads, auth, fivetran  # noqa: E402
from .agent_pool import close_all  # noqa: E402

APP_NAME = "Zero-to-Synced"


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_service = DatabaseSessionService(
        db_url=get_db_url(), connect_args={"ssl": True}
    )
    await init_tables()

    app.state.session_service = session_service
    app.state.session_locks = {}  # session_id -> asyncio.Lock

    yield

    await close_all()  # shut down any per-user MCP subprocesses


app = FastAPI(title="Zero-to-Synced API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Same-origin in production (the API serves the built frontend), so CORS is
# only needed for local dev or a split deploy. Override with CORS_ORIGINS
# (comma-separated) when the frontend is hosted on a different origin.
_default_origins = "http://localhost:5173,http://localhost:3000"
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(fivetran.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def get_session_lock(session_id: str) -> asyncio.Lock:
    locks = app.state.session_locks
    if session_id not in locks:
        locks[session_id] = asyncio.Lock()
    return locks[session_id]


# Serve the built React app (frontend/dist) as a same-origin SPA, if present.
# Mounted last so it never shadows the /api routes above. No-ops in local dev
# where you run Vite separately and there's no dist/ yet.
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
