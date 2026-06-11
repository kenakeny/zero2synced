import uuid
<<<<<<< HEAD
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

from ..db import get_engine
=======
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text

from ..db import get_engine
from ..auth import get_current_user, assert_session_owner
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
from ..schemas import SessionInfo, HistoryMessage

router = APIRouter(tags=["sessions"])

APP_NAME = "Zero-to-Synced"
<<<<<<< HEAD
USER_ID = "user"  # single-tenant for the hackathon; sessions are the isolation unit


@router.post("/sessions")
async def create_session(request: Request):
    session_id = str(uuid.uuid4())
    await request.app.state.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
=======


@router.post("/sessions")
async def create_session(request: Request, user_id: str = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    # ADK isolates conversation state by user_id; use the real authenticated user.
    await request.app.state.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
    )
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
<<<<<<< HEAD
            text("INSERT INTO app_sessions (id) VALUES (:id)"), {"id": session_id}
=======
            text("INSERT INTO app_sessions (id, user_id) VALUES (:id, :uid)"),
            {"id": session_id, "uid": user_id},
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
        )
    return {"session_id": session_id}


@router.get("/sessions", response_model=list[SessionInfo])
<<<<<<< HEAD
async def list_sessions():
=======
async def list_sessions(user_id: str = Depends(get_current_user)):
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
    engine = get_engine()
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT id, title, created_at, last_active "
<<<<<<< HEAD
                    "FROM app_sessions ORDER BY last_active DESC"
                )
=======
                    "FROM app_sessions WHERE user_id = :uid ORDER BY last_active DESC"
                ),
                {"uid": user_id},
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
            )
        ).fetchall()
    return [
        SessionInfo(
            session_id=r.id, title=r.title,
            created_at=r.created_at, last_active=r.last_active,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}/history", response_model=list[HistoryMessage])
<<<<<<< HEAD
async def get_history(session_id: str, request: Request):
    session = await request.app.state.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
=======
async def get_history(
    session_id: str, request: Request, user_id: str = Depends(get_current_user)
):
    await assert_session_owner(session_id, user_id)
    session = await request.app.state.session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
>>>>>>> edf78e1393db046fe4ab4e67ca35afc838e3f885
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages: list[HistoryMessage] = []
    for event in session.events:
        if not event.content or not event.content.parts:
            continue
        texts = [p.text for p in event.content.parts if getattr(p, "text", None)]
        if not texts:
            continue  # skip pure tool-call/result events
        role = "user" if event.content.role == "user" else "agent"
        messages.append(
            HistoryMessage(role=role, text="\n".join(texts), timestamp=event.timestamp)
        )
    return messages
