from fastapi.responses import JSONResponse
import httpx
import asyncio
from fastapi import HTTPException

genderize_url = "https://api.genderize.io/?name="
agify_url = "https://api.agify.io/?name="
nationalize_url = "https://api.nationalize.io/?name="

async def get_data(name: str):
    try:
        async with httpx.AsyncClient() as client:

            gender_task = client.get(
                f"{genderize_url}{name}",
                timeout=4.0
            )

            age_task = client.get(
                f"{agify_url}{name}",
                timeout=4.0
            )

            nationality_task = client.get(
                f"{nationalize_url}{name}",
                timeout=4.0
            )

            gender_response, age_response, nationality_response = await asyncio.gather(
                gender_task,
                age_task,
                nationality_task
            )

            responses = [
                gender_response,
                age_response,
                nationality_response
            ]

            for response in responses:
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "status": "error",
                            "message": "Profile not found"
                        }
                    )

            return {
                "gender_data": gender_response.json(),
                "age_data": age_response.json(),
                "nationality_data": nationality_response.json()
            }

    except httpx.HTTPError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Upstream or Server Failure"
            }
        )