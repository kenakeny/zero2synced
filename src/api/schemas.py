from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str


class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    last_active: datetime


class HistoryMessage(BaseModel):
    role: str
    text: str
    timestamp: float


class UploadInfo(BaseModel):
    file_id: str
    filename: str
    status: str
    row_count: int | None = None
    columns: list[str] | None = None
