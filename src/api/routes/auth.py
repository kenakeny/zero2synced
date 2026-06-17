import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from ..db import get_engine
from ..auth import hash_password, verify_password, make_token, get_current_user
from ..schemas import Credentials, AuthResponse, UserInfo
from ..app import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup(request: Request, body: Credentials):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    email = body.email.lower()
    engine = get_engine()
    async with engine.begin() as conn:
        exists = (
            await conn.execute(
                text("SELECT 1 FROM users WHERE email = :email"), {"email": email}
            )
        ).first()
        if exists:
            raise HTTPException(status_code=409, detail="That email is already registered.")

        user_id = str(uuid.uuid4())
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash) "
                "VALUES (:id, :email, :ph)"
            ),
            {"id": user_id, "email": email, "ph": hash_password(body.password)},
        )

    return AuthResponse(
        token=make_token(user_id), user=UserInfo(id=user_id, email=email)
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: Credentials):
    email = body.email.lower()
    engine = get_engine()
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT id, password_hash FROM users WHERE email = :email"),
                {"email": email},
            )
        ).first()

    if row is None or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    return AuthResponse(
        token=make_token(row.id), user=UserInfo(id=row.id, email=email)
    )


@router.get("/me", response_model=UserInfo)
async def me(user_id: str = Depends(get_current_user)):
    engine = get_engine()
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT id, email FROM users WHERE id = :id"), {"id": user_id}
            )
        ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return UserInfo(id=row.id, email=row.email)
