from fastapi import Query, Request, Response, status
from request_func.genderize import gender_profile
from request_func.agify import agify_profile
from request_func.nationalize import nationalize_profile
from middleware.validate_name import validate_name
from uuid6 import uuid7
from datetime import datetime, timezone
from database import db
import asyncio


def format_profile(profile):
    return {
        "id": str(profile["id"]),
        "name": profile["name"],
        "gender": profile["gender"],
        "gender_probability": profile["gender_probability"],
        "sample_size": profile["sample_size"],
        "age": profile["age"],
        "age_group": profile["age_group"],
        "country_id": profile["country_id"],
        "country_probability": profile["country_probability"],
        "created_at": profile["created_at"].isoformat().replace("+00:00", "Z")
    }


async def api_profiles_post(
    name: str = Query(None)
):
    if validate_name(name):
        return validate_name(name)

    normalised_name = name.strip().lower()

    async with db.pool.acquire() as conn:

        existing_profile = await conn.fetchrow(
            "SELECT * FROM profiles WHERE name = $1",
            normalised_name
        )

        if existing_profile:

            existing_profile = dict(existing_profile)

            return {
                "status": "success",
                "message": "Profile already exists",
                "data": format_profile(existing_profile)
            }
    
    gender_data, age_data, nat_data = await asyncio.gather(
        gender_profile(normalised_name),
        agify_profile(normalised_name),
        nationalize_profile(normalised_name)
    )

    profile = {
        "id": str(uuid7()),
        "name": normalised_name,
        "gender": gender_data.get("gender"),
        "gender_probability": gender_data.get("gender_probability"),
        "sample_size": gender_data.get("sample_size"),
        "age": age_data.get("age"),
        "age_group": age_data.get("age_group"),
        "country_id": nat_data.get("country_id"),
        "country_probability": nat_data.get("country_probability"),
        "created_at": datetime.now(timezone.utc)
    }

    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO profiles (
                id, created_at, name,
                gender, gender_probability, sample_size,
                age, age_group,
                country_id, country_probability
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
            profile["id"],
            profile["created_at"],
            profile["name"],
            profile["gender"],
            profile["gender_probability"],
            profile["sample_size"],
            profile["age"],
            profile["age_group"],
            profile["country_id"],
            profile["country_probability"]
        )

    return {
        "status": "success",
        "data": format_profile(profile)
    }