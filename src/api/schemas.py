from pydantic import BaseModel, EmailStr
from datetime import datetime


class Credentials(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserInfo


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
