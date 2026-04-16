from database import db
from uuid import UUID


from database import db
from uuid import UUID


async def get_all_profiles(
    gender: str = None,
    country_id: str = None,
    age_group: str = None
):
    async with db.pool.acquire() as conn:

        query = """
            SELECT id, name, gender, age, age_group, country_id
            FROM profiles
        """

        conditions = []
        params = []
        index = 1

        if gender:
            conditions.append(f"LOWER(gender) = LOWER(${index})")
            params.append(gender)
            index += 1

        if country_id:
            conditions.append(f"LOWER(country_id) = LOWER(${index})")
            params.append(country_id)
            index += 1

        if age_group:
            conditions.append(f"LOWER(age_group) = LOWER(${index})")
            params.append(age_group)
            index += 1

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = await conn.fetch(query, *params)

        return {
            "status": "success",
            "count": len(rows),
            "data": [dict(r) for r in rows]
        }


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