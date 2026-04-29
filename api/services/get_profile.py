from dotenv import load_dotenv
import os
load_dotenv()

if os.getenv("MODULE_ENV") == 'development':
    from database import db
else:
    from api.database import db

from uuid import UUID

async def get_all_profiles(
    gender: str = None,
    country_id: str = None,
    age_group: str = None,
    min_age: int = None,
    max_age: int = None,
    min_gender_probability: float = None,
    min_country_probability: float = None,
    sort_by: str = None,
    order: str = "asc",
    page: int = 1,
    limit: int = 10,
):
    VALID_SORT = {"age", "created_at", "gender_probability"}
    VALID_ORDER = {"asc", "desc"}

    if sort_by and sort_by not in VALID_SORT:
        return None, {"status": "error", "message": "Invalid query parameters"}
    if order not in VALID_ORDER:
        return None, {"status": "error", "message": "Invalid query parameters"}
    if limit > 50:
        limit = 50

    conditions = []
    params = []
    i = 1

    if gender:
        conditions.append(f"LOWER(gender) = LOWER(${i})"); params.append(gender); i+=1
    if country_id:
        conditions.append(f"LOWER(country_id) = LOWER(${i})"); params.append(country_id); i+=1
    if age_group:
        conditions.append(f"LOWER(age_group) = LOWER(${i})"); params.append(age_group); i+=1
    if min_age is not None:
        conditions.append(f"age >= ${i}"); params.append(min_age); i+=1
    if max_age is not None:
        conditions.append(f"age <= ${i}"); params.append(max_age); i+=1
    if min_gender_probability is not None:
        conditions.append(f"gender_probability >= ${i}"); params.append(min_gender_probability); i+=1
    if min_country_probability is not None:
        conditions.append(f"country_probability >= ${i}"); params.append(min_country_probability); i+=1

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sort_clause = f" ORDER BY {sort_by} {order.upper()}" if sort_by else ""
    offset = (page - 1) * limit

    async with db.pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM profiles{where}", *params)
        rows = await conn.fetch(
            f"SELECT * FROM profiles{where}{sort_clause} LIMIT ${i} OFFSET ${i+1}",
            *params, limit, offset
        )

    total_pages = (total + limit - 1) // limit if total > 0 else 0
    base_url = f"/api/profiles"
    query = f"page={{page}}&limit={limit}"

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
            "self": f"{base_url}?{query.format(page=page)}",
            "next": f"{base_url}?{query.format(page=page+1)}" if page < total_pages else None,
            "prev": f"{base_url}?{query.format(page=page-1)}" if page > 1 else None,
        },
        "data": [dict(r) for r in rows]
    }, None


async def get_profile_by_id(id: UUID):
    async with db.pool.acquire() as conn:
        profile = await conn.fetchrow(
            "SELECT * FROM profiles WHERE id = $1",
            id
        )

        if not profile:
            return {
                "status": "error",
                "message": "Profile not found",
                "data": None
            }

        return {
            "status": "success",
            "data": dict(profile)
        }