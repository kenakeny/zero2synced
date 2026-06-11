import json
from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from google.genai import types
from google.adk.agents.run_config import RunConfig, StreamingMode

from ..db import get_engine
from ..schemas import ChatRequest

router = APIRouter(tags=["chat"])

APP_NAME = "Zero-to-Synced"
USER_ID = "user"


async def run_agent_turn(request: Request, session_id: str, message_text: str):
    """Yields SSE events: token / tool / done / error."""
    runner = request.app.state.runner

    message = types.Content(role="user", parts=[types.Part(text=message_text)])
    final_text = ""

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            # tool activity — lets the frontend show "talking to Fivetran..."
            for call in event.get_function_calls():
                yield {"event": "tool", "data": json.dumps(
                    {"name": call.name, "status": "running"})}
            for resp in event.get_function_responses():
                yield {"event": "tool", "data": json.dumps(
                    {"name": resp.name, "status": "done"})}

            # streamed model text
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        if event.partial:
                            yield {"event": "token", "data": json.dumps(
                                {"text": part.text})}
                        elif event.is_final_response():
                            final_text = part.text

        yield {"event": "done", "data": json.dumps({"text": final_text})}

    except Exception as e:  # surface as a plain-English SSE error, not a 500
        yield {"event": "error", "data": json.dumps(
            {"message": f"Something went wrong talking to the agent: {e}"})}


@router.post("/sessions/{session_id}/chat")
async def chat(session_id: str, body: ChatRequest, request: Request):
    session = await request.app.state.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from ..app import get_session_lock
    lock = get_session_lock(session_id)

    async def event_stream():
        async with lock:  # one in-flight turn per session
            async for sse_event in run_agent_turn(request, session_id, body.message):
                yield sse_event
        # touch last_active for the session list ordering
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE app_sessions SET last_active = now() WHERE id = :id"),
                {"id": session_id},
            )

    return EventSourceResponse(event_stream())
