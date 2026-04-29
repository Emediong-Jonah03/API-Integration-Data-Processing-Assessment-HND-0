from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import APIRouter, Query, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import csv
import io
from datetime import datetime

if os.getenv("MODULE_ENV") == 'development':
    from services.create_profile_service import api_profiles_post
    from services.get_profile import get_all_profiles, get_profile_by_id
    from services.delete_profile import delete_profile
    from services.search_profiles_nl import search_profiles_nl
    from auth.dependencies import get_current_user, require_role
else:
    from api.services.create_profile_service import api_profiles_post
    from api.services.get_profile import get_all_profiles, get_profile_by_id
    from api.services.delete_profile import delete_profile
    from api.services.search_profiles_nl import search_profiles_nl
    from api.auth.dependencies import get_current_user, require_role


profileRouter = APIRouter(redirect_slashes=False)

class ProfileRequest(BaseModel):
    name: str


def check_api_version(x_api_version: Optional[str] = Header(None)):
    if x_api_version != "1":
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "API version header required"}
        )


# POST - admin only
@profileRouter.post("/", status_code=201, dependencies=[Depends(check_api_version)])
async def api_profiles(
    body: ProfileRequest,
    current_user: dict = Depends(require_role("admin")),
):
    return await api_profiles_post(body.name)


# SEARCH - all authenticated users
@profileRouter.get("/search", dependencies=[Depends(check_api_version)])
async def api_profiles_search(
    q: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    return await search_profiles_nl(q, page=page, limit=limit)


# EXPORT - all authenticated users
@profileRouter.get("/export", dependencies=[Depends(check_api_version)])
async def api_profiles_export(
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: str = Query("asc"),
    current_user: dict = Depends(get_current_user),
):
    result, err = await get_all_profiles(
        gender=gender,
        country_id=country_id,
        age_group=age_group,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        order=order,
        page=1,
        limit=100000,
    )
    if err:
        return JSONResponse(status_code=400, content=err)

    profiles = result.get("data", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "gender", "gender_probability",
        "age", "age_group", "country_id", "country_name",
        "country_probability", "created_at"
    ])
    for p in profiles:
        writer.writerow([
            p.get("id"), p.get("name"), p.get("gender"),
            p.get("gender_probability"), p.get("age"),
            p.get("age_group"), p.get("country_id"),
            p.get("country_name"), p.get("country_probability"),
            p.get("created_at"),
        ])

    output.seek(0)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=profiles_{timestamp}.csv"}
    )


# LIST - all authenticated users
@profileRouter.get("/", dependencies=[Depends(check_api_version)])
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
    current_user: dict = Depends(get_current_user),
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


# GET BY ID - all authenticated users
@profileRouter.get("/{id}", dependencies=[Depends(check_api_version)])
async def api_profiles_get_by_id(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    return await get_profile_by_id(id)


# DELETE - admin only
@profileRouter.delete("/{id}", status_code=204, dependencies=[Depends(check_api_version)])
async def api_profiles_delete(
    id: str,
    current_user: dict = Depends(require_role("admin")),
):
    return await delete_profile(id)