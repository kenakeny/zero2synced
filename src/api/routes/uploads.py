import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text

from ..db import get_engine
from ..auth import get_current_user, assert_session_owner
from ..agent_pool import get_runner
from ..ingestion import parse_file, upload_to_s3, build_agent_notification
from ..schemas import UploadInfo
from .chat import run_agent_turn

router = APIRouter(tags=["uploads"])

UPLOAD_DIR = Path("uploads")


@router.post("/sessions/{session_id}/files")
async def upload_file(
    session_id: str,
    file: UploadFile,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    await assert_session_owner(session_id, user_id)

    runner = await get_runner(request.app, user_id)
    if runner is None:
        raise HTTPException(
            status_code=409, detail="Connect your Fivetran account first to start syncing."
        )

    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    try:
        parsed = parse_file(file.filename, raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_id = str(uuid.uuid4())

    # keep the original on disk (never in Postgres)
    UPLOAD_DIR.mkdir(exist_ok=True)
    (UPLOAD_DIR / f"{file_id}_{file.filename}").write_bytes(raw)

    s3_key = f"uploads/{session_id}/{file_id}.csv"
    s3_uri = upload_to_s3(parsed.csv_bytes, s3_key)
    status = "uploaded_to_s3" if s3_uri else "context_only"

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO uploads (id, session_id, filename, s3_key, status, row_count, columns) "
                "VALUES (:id, :sid, :fn, :key, :st, :rc, :cols)"
            ),
            {
                "id": file_id, "sid": session_id, "fn": file.filename,
                "key": s3_key if s3_uri else None, "st": status,
                "rc": parsed.row_count, "cols": json.dumps(parsed.columns),
            },
        )

    # tell the agent about the file; stream its reaction back as SSE
    notification = build_agent_notification(file.filename, parsed, s3_uri)

    from ..app import get_session_lock
    lock = get_session_lock(session_id)

    async def event_stream():
        yield {"event": "file", "data": json.dumps({
            "file_id": file_id, "filename": file.filename, "status": status,
            "row_count": parsed.row_count, "columns": parsed.columns,
        })}
        async with lock:
            async for sse_event in run_agent_turn(runner, session_id, notification, user_id):
                yield sse_event

    return EventSourceResponse(event_stream())


@router.get("/sessions/{session_id}/files", response_model=list[UploadInfo])
async def list_files(session_id: str, user_id: str = Depends(get_current_user)):
    await assert_session_owner(session_id, user_id)
    engine = get_engine()
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT id, filename, status, row_count, columns "
                    "FROM uploads WHERE session_id = :sid ORDER BY created_at DESC"
                ),
                {"sid": session_id},
            )
        ).fetchall()
    return [
        UploadInfo(
            file_id=r.id, filename=r.filename, status=r.status,
            row_count=r.row_count,
            columns=json.loads(r.columns) if r.columns else None,
        )
        for r in rows
    ]
