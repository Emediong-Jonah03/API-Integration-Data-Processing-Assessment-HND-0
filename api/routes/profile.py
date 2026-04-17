from fastapi import APIRouter, Request, Query
from api.services.create_profile_service import api_profiles_post
from api.services.get_profile import get_all_profiles, get_profile_by_id
from api.services.delete_profile import delete_profile
from pydantic import BaseModel

profileRouter = APIRouter()

class ProfileRequest(BaseModel):
    name: str

@profileRouter.post("/", status_code=201)
async def api_profiles(body: ProfileRequest):
    return await api_profiles_post(body.name)


@profileRouter.get("/")
async def api_profiles_get(
    gender: str = Query(None),
    country_id: str = Query(None),
    age_group: str = Query(None),
):
    return await get_all_profiles(gender, country_id, age_group)

@profileRouter.get("/{id}")
async def api_profiles_get_by_id(id: str):
    return await get_profile_by_id(id)

@profileRouter.delete("/{id}", status_code=204)
async def api_profiles_delete(id: str):
    return await delete_profile(id)
            