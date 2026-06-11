# Routes for a user to connect/disconnect their own Fivetran account.
import base64

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import get_current_user
from ..fivetran_store import save_credentials, delete_credentials, has_credentials
from ..agent_pool import invalidate

router = APIRouter(prefix="/fivetran", tags=["fivetran"])

FIVETRAN_API = "https://api.fivetran.com/v1/groups"


class FivetranKeys(BaseModel):
    api_key: str
    api_secret: str


async def _validate(api_key: str, api_secret: str) -> None:
    """Confirm the keys actually work before we store them."""
    token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                FIVETRAN_API, headers={"Authorization": f"Basic {token}"}
            )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502, detail="Couldn't reach Fivetran to verify the keys. Try again."
        )
    if resp.status_code == 401:
        raise HTTPException(status_code=400, detail="That Fivetran API key or secret is incorrect.")
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"Fivetran rejected the keys (status {resp.status_code}).",
        )


@router.get("/status")
async def status(user_id: str = Depends(get_current_user)):
    return {"connected": await has_credentials(user_id)}


@router.post("/connect")
async def connect(
    body: FivetranKeys, request: Request, user_id: str = Depends(get_current_user)
):
    key = body.api_key.strip()
    secret = body.api_secret.strip()
    if not key or not secret:
        raise HTTPException(status_code=400, detail="Enter both your API key and secret.")

    await _validate(key, secret)
    await save_credentials(user_id, key, secret)
    await invalidate(user_id)  # rebuild the agent with the new keys on next use
    return {"connected": True}


@router.delete("/disconnect")
async def disconnect(user_id: str = Depends(get_current_user)):
    await delete_credentials(user_id)
    await invalidate(user_id)
    return {"connected": False}
