# Per-user Fivetran credentials, encrypted at rest.
#
# Unlike passwords (one-way hashed), these must be reversible because the agent
# needs the real key/secret to talk to Fivetran. We encrypt with Fernet using a
# key derived from JWT_SECRET (override with FERNET_KEY if you prefer).
import base64
import hashlib
import os

from cryptography.fernet import Fernet
from sqlalchemy import text

from .db import get_engine


def _fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        secret = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key if isinstance(key, bytes) else key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


async def save_credentials(user_id: str, api_key: str, api_secret: str) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO fivetran_credentials (user_id, api_key_enc, api_secret_enc) "
                "VALUES (:uid, :k, :s) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "api_key_enc = EXCLUDED.api_key_enc, "
                "api_secret_enc = EXCLUDED.api_secret_enc, "
                "updated_at = now()"
            ),
            {"uid": user_id, "k": encrypt(api_key), "s": encrypt(api_secret)},
        )


async def get_credentials(user_id: str) -> tuple[str, str] | None:
    engine = get_engine()
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT api_key_enc, api_secret_enc "
                    "FROM fivetran_credentials WHERE user_id = :uid"
                ),
                {"uid": user_id},
            )
        ).first()
    if row is None:
        return None
    return decrypt(row.api_key_enc), decrypt(row.api_secret_enc)


async def has_credentials(user_id: str) -> bool:
    engine = get_engine()
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT 1 FROM fivetran_credentials WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).first()
    return row is not None


async def delete_credentials(user_id: str) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM fivetran_credentials WHERE user_id = :uid"),
            {"uid": user_id},
        )
