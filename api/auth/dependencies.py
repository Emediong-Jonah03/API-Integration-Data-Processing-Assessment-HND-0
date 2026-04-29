import os
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

if os.getenv("MODULE_ENV") == 'development':
    from auth.jwt import decode_access_token
    from database.db import get_db
else:
    from api.auth.jwt import decode_access_token
    from api.database.db import get_db

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(401, detail={"status": "error", "message": "Invalid or expired token"})

    user = await db.fetchrow(
        "SELECT id, username, role, is_active FROM users WHERE id = $1",
        payload["sub"]
    )

    if not user:
        raise HTTPException(401, detail={"status": "error", "message": "User not found"})

    if not user["is_active"]:
        raise HTTPException(403, detail={"status": "error", "message": "Account is inactive"})

    return dict(user)


def require_role(*roles: str):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(403, detail={"status": "error", "message": "Access denied"})
        return current_user
    return role_checker