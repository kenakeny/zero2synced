# FastAPI entrypoint. Agents are created per-user from each user's stored
# Fivetran keys (see agent_pool), so we do NOT build a shared agent at startup.
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.sessions import DatabaseSessionService

load_dotenv()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
