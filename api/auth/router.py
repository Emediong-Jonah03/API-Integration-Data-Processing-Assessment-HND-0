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
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")

pkce_store: dict = {}


@router.get("/auth/github")
@limiter.limit("10/minute")
async def github_login(
    request: Request,
    code_challenge: str = Query(...),
    source: str = Query(default="cli")
):
    state = secrets.token_urlsafe(32)
    pkce_store[state] = {"challenge": code_challenge, "source": source}

    if source == "cli":
        redirect_uri = "http://localhost:8080/callback"
    else:
        redirect_uri = GITHUB_REDIRECT_URI

    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
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
    code_verifier: str = Query(...),
    db=Depends(get_db),
):
    stored = pkce_store.pop(state, None)
    if not stored:
        raise HTTPException(400, detail={"status": "error", "message": "Invalid or expired state"})

    stored_challenge = stored["challenge"]
    source = stored["source"]

    computed_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    if computed_challenge != stored_challenge:
        raise HTTPException(400, detail={"status": "error", "message": "PKCE verification failed"})

    if source == "cli":
        redirect_uri = "http://localhost:8080/callback"
    else:
        redirect_uri = GITHUB_REDIRECT_URI

    async with httpx.AsyncClient() as client:
        gh_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        gh_data = gh_resp.json()

    gh_access_token = gh_data.get("access_token")
    if not gh_access_token:
        raise HTTPException(400, detail={"status": "error", "message": f"GitHub token exchange failed: {gh_data}"})

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {gh_access_token}",
                "Accept": "application/json",
            },
        )
        github_user = user_resp.json()

    user = await upsert_user(db, github_user)
    if not user["is_active"]:
        raise HTTPException(403, detail={"status": "error", "message": "Account is inactive"})

    access_token = create_access_token({
        "sub": str(user["id"]),
        "role": user["role"],
        "username": user["username"],
    })
    raw_refresh = generate_refresh_token()
    await store_refresh_token(db, str(user["id"]), raw_refresh)

    if source == "web":
        web_url = os.getenv("WEB_URL", "http://localhost:5173")
        redirect_response = RedirectResponse(f"{web_url}/dashboard")
        redirect_response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax", max_age=180)
        redirect_response.set_cookie(key="refresh_token", value=raw_refresh, httponly=True, samesite="lax", max_age=300)
        return redirect_response

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