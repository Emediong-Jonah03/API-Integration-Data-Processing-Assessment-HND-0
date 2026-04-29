import hashlib
import base64
import os
import secrets
import httpx

from fastapi import APIRouter, Query, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

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

load_dotenv()

router = APIRouter(tags=["auth"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

# Temporary in-memory state store for PKCE
pkce_store: dict[str, str] = {}


@router.get("/auth/github")
@limiter.limit("10/minute")
async def github_login(request: Request, code_challenge: str = Query(...)):
    state = secrets.token_urlsafe(32)
    pkce_store[state] = code_challenge

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
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
    code_verifier: str = Query(...),
    db=Depends(get_db),
):
    # 1. Validate state
    stored_challenge = pkce_store.pop(state, None)
    if not stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "Invalid or expired state"})

    # 2. Verify PKCE
    computed_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    if computed_challenge != stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "PKCE verification failed"})

    # 3. Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        gh_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )
        gh_data = gh_resp.json()

    gh_access_token = gh_data.get("access_token")
    if not gh_access_token:
        raise HTTPException(400, detail={"status": "error", "message": f"GitHub token exchange failed: {gh_data}"})

    # 4. Fetch GitHub user
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {gh_access_token}",
                "Accept": "application/json",
            },
        )
        github_user = user_resp.json()

    # 5. Upsert user in DB
    user = await upsert_user(db, github_user)

    if not user["is_active"]:
        raise HTTPException(403, detail={"status": "error", "message": "Account is inactive"})

    # 6. Issue tokens
    access_token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
        "username": user["username"],
    })
    raw_refresh = generate_refresh_token()
    await store_refresh_token(db, str(user["id"]), raw_refresh)

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "role": user["role"],
        "username": user["username"],
    }


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
async def logout(request: Request, body: dict, db=Depends(get_db)):
    refresh = body.get("refresh_token")
    if not refresh:
        raise HTTPException(400, detail={"status": "error", "message": "refresh_token required"})

    await db.execute("""
        UPDATE refresh_tokens SET revoked = TRUE
        WHERE token_hash = $1
    """, hash_token(refresh))

    return {"status": "success", "message": "Logged out"}


@router.get("/auth/github/callback/web")
@limiter.limit("10/minute")
async def github_callback_web(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    code_verifier: str = Query(...),
    db=Depends(get_db),
):
    # 1. Validate state
    stored_challenge = pkce_store.pop(state, None)
    if not stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "Invalid or expired state"})

    # 2. Verify PKCE
    computed_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    if computed_challenge != stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "PKCE verification failed"})

    # 3. Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        gh_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": os.getenv("GITHUB_WEB_REDIRECT_URI"),
            },
            headers={"Accept": "application/json"},
        )
        gh_data = gh_resp.json()

    gh_access_token = gh_data.get("access_token")
    if not gh_access_token:
        raise HTTPException(400, detail={"status": "error", "message": f"GitHub token exchange failed: {gh_data}"})

    # 4. Fetch GitHub user
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {gh_access_token}",
                "Accept": "application/json",
            },
        )
        github_user = user_resp.json()

    # 5. Upsert user
    user = await upsert_user(db, github_user)
    if not user["is_active"]:
        raise HTTPException(403, detail={"status": "error", "message": "Account is inactive"})

    # 6. Issue tokens
    access_token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
        "username": user["username"],
    })
    raw_refresh = generate_refresh_token()
    await store_refresh_token(db, str(user["id"]), raw_refresh)

    # 7. Set HttpOnly cookies and redirect
    redirect_response = RedirectResponse("http://localhost:5173/dashboard")
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=180,
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite="lax",
        max_age=300,
    )
    return redirect_response
auth_router = router