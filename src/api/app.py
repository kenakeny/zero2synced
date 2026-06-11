# FastAPI entrypoint. One shared agent/runner/MCP toolset for the whole app —
# the MCP server is a subprocess, so we create it once at startup, not per request.
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

load_dotenv()

from ..agent.agent import create_agent  # noqa: E402
from .db import init_tables, get_db_url  # noqa: E402
from .routes import chat, sessions, uploads  # noqa: E402

APP_NAME = "Zero-to-Synced"


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent, mcp_toolset = await create_agent()
    session_service = DatabaseSessionService(
        db_url=get_db_url(), connect_args={"ssl": True}
    )
    await init_tables()

    app.state.runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    app.state.session_service = session_service
    app.state.mcp_toolset = mcp_toolset
    app.state.session_locks = {}  # session_id -> asyncio.Lock

    yield

    await mcp_toolset.close()


app = FastAPI(title="Zero-to-Synced API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
