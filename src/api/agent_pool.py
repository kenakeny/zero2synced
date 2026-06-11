# One Fivetran-connected agent per user, created lazily from their stored keys
# and reused across requests. The MCP server is a subprocess, so we cache the
# toolset rather than spawning one per message.
import asyncio

from google.adk.runners import Runner

from ..agent.agent import create_agent
from .fivetran_store import get_credentials

APP_NAME = "Zero-to-Synced"

_pool: dict[str, dict] = {}      # user_id -> {"runner", "toolset"}
_locks: dict[str, asyncio.Lock] = {}


def _lock(user_id: str) -> asyncio.Lock:
    if user_id not in _locks:
        _locks[user_id] = asyncio.Lock()
    return _locks[user_id]


async def get_runner(app, user_id: str):
    """Return this user's Runner, or None if they haven't connected Fivetran."""
    if user_id in _pool:
        return _pool[user_id]["runner"]

    async with _lock(user_id):
        if user_id in _pool:  # built while we waited for the lock
            return _pool[user_id]["runner"]

        creds = await get_credentials(user_id)
        if not creds:
            return None

        api_key, api_secret = creds
        agent, toolset = await create_agent(api_key=api_key, api_secret=api_secret)
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=app.state.session_service,
        )
        _pool[user_id] = {"runner": runner, "toolset": toolset}
        return runner


async def invalidate(user_id: str) -> None:
    """Drop a user's cached agent (e.g. after they reconnect with new keys)."""
    entry = _pool.pop(user_id, None)
    if entry:
        try:
            await entry["toolset"].close()
        except Exception:
            pass


async def close_all() -> None:
    for entry in list(_pool.values()):
        try:
            await entry["toolset"].close()
        except Exception:
            pass
    _pool.clear()
