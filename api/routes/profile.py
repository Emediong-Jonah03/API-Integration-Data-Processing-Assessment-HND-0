from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

if os.getenv("MODULE_ENV") == 'development':
    from services.create_profile_service import api_profiles_post
    from services.get_profile import get_all_profiles, get_profile_by_id
    from services.delete_profile import delete_profile
    from services.search_profiles_nl import search_profiles_nl
else:
    from api.services.create_profile_service import api_profiles_post
    from api.services.get_profile import get_all_profiles, get_profile_by_id
    from api.services.delete_profile import delete_profile
    from api.services.search_profiles_nl import search_profiles_nl


profileRouter = APIRouter(redirect_slashes=False)

class ProfileRequest(BaseModel):
    name: str


@profileRouter.post("/", status_code=201)
async def api_profiles(body: ProfileRequest):
    return await api_profiles_post(body.name)


@profileRouter.get("/search")
async def api_profiles_search(
    q: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    return await search_profiles_nl(q, page=page, limit=limit)


@profileRouter.get("/")
async def api_profiles_get(
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    min_gender_probability: Optional[float] = Query(None),
    min_country_probability: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    result, err = await get_all_profiles(
        gender=gender,
        country_id=country_id,
        age_group=age_group,
        min_age=min_age,
        max_age=max_age,
        min_gender_probability=min_gender_probability,
        min_country_probability=min_country_probability,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )
    if err:
        return JSONResponse(status_code=400, content=err)
    return result


@profileRouter.get("/{id}")
async def api_profiles_get_by_id(id: str):
    return await get_profile_by_id(id)


@profileRouter.delete("/{id}", status_code=204)
async def api_profiles_delete(id: str):
    return await delete_profile(id)