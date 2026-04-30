import os
from fastapi import APIRouter, Depends

if os.getenv("MODULE_ENV") == 'development':
    from auth.dependencies import get_current_user
else:
    from api.auth.dependencies import get_current_user

usersRouter = APIRouter(tags=["users"])

@usersRouter.get("/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
        }
    }