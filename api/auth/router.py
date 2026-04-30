import hashlib
import base64
import os
import secrets
import httpx

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

if os.getenv("MODULE_ENV") == 'development':
    from database.db import get_db
    from database.users import upsert_user
    from database.token import store_refresh_token, rotate_refresh_token, hash_token
    from auth.jwt import create_access_token, generate_refresh_token
else:
    from api.database.db import get_db
    from api.database.users import upsert_user
    from api.database.token import store_refresh_token, rotate_refresh_token, hash_token
    from api.auth.jwt import create_access_token, generate_refresh_token

router = APIRouter(tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CLI_CLIENT_ID = os.getenv("GITHUB_CLI_CLIENT_ID")
GITHUB_CLI_CLIENT_SECRET = os.getenv("GITHUB_CLI_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

pkce_store: dict = {}


import json
from base64 import urlsafe_b64encode, urlsafe_b64decode

# Remove pkce_store dict entirely

@router.get("/auth/github")
@limiter.limit("10/minute")
async def github_login(
    request: Request,
    code_challenge: str = Query(...),
    source: str = Query(default="cli"),
    code_verifier: str = Query(default=None),
):
    state_data = json.dumps({
        "challenge": code_challenge,
        "source": source,
        "verifier": code_verifier or "",
    })
    state = urlsafe_b64encode(state_data.encode()).decode()

    if source == "cli":
        client_id = GITHUB_CLI_CLIENT_ID
        redirect_uri = "http://localhost:8080/callback"
    else:
        client_id = GITHUB_CLIENT_ID
        redirect_uri = GITHUB_REDIRECT_URI

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user user:email"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/auth/github/callback")
@limiter.limit("10/minute")
async def github_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    code_verifier: str = Query(default=None),
    db=Depends(get_db),
):
    try:
        state_data = json.loads(urlsafe_b64decode(state.encode()).decode())
        stored_challenge = state_data["challenge"]
        source = state_data["source"]
        state_verifier = state_data.get("verifier", "")
    except Exception:
        raise HTTPException(400, detail={"status": "error", "message": "Invalid state"})

    # CLI sends verifier as query param, web encodes it in state
    final_verifier = code_verifier if source == "cli" else state_verifier

    computed_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(final_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    if computed_challenge != stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "PKCE verification failed"})

@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, body: dict, db=Depends(get_db)):
    old_refresh = body.get("refresh_token")
    if not old_refresh:
        raise HTTPException(400, detail={"status": "error", "message": "refresh_token required"})

    new_refresh = generate_refresh_token()

    try:
        user_id = await rotate_refresh_token(db, old_refresh, new_refresh)
    except ValueError as e:
        raise HTTPException(401, detail={"status": "error", "message": str(e)})

    row = await db.fetchrow(
        "SELECT id, role, username, is_active FROM users WHERE id = $1", user_id
    )
    if not row or not row["is_active"]:
        raise HTTPException(403, detail={"status": "error", "message": "Account inactive"})

    access_token = create_access_token({
        "sub": str(row["id"]),
        "role": row["role"],
        "username": row["username"],
    })

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": new_refresh,
    }


@router.post("/auth/logout")
@limiter.limit("10/minute")
async def logout(request: Request, body: dict, db=Depends(get_db)):
    refresh = body.get("refresh_token")
    if not refresh:
        raise HTTPException(400, detail={"status": "error", "message": "refresh_token required"})

    await db.execute("""
        UPDATE refresh_tokens SET revoked = TRUE
        WHERE token_hash = $1
    """, hash_token(refresh))

    return {"status": "success", "message": "Logged out"}


auth_router = router