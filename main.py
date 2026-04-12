from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_data(name: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.genderize.io/?name={name}",
                timeout=4.0
            )
            return response.json()

    except httpx.HTTPStatusException:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Server Failure"
        })



@app.get("/api/classify")
async def classify_name(name: str = Query(default=None)):

    if name is None or name.strip() == "":
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Missing or empty name parameter"
        })

    try:
        float(name) 
        return JSONResponse(status_code=422, content={
            "status": "error",
            "message": "name is not a string"
        })
    except ValueError:
        pass

    data = await get_data(name)

    if isinstance(data, JSONResponse):
        return data

    if data.get("gender") is None or data.get("count", 0) == 0:
        return JSONResponse(status_code=200, content={
            "status": "error",
            "message": "No prediction available for the provided name"
        })

    probability = data["probability"]
    sample_size = data["count"]
    is_confident = probability >= 0.7 and sample_size >= 100

    return JSONResponse(status_code=200, content={
        "status": "success",
        "data": {
            "name": data["name"],
            "gender": data["gender"],
            "probability": probability,
            "sample_size": sample_size,
            "is_confident": is_confident,
            "processed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
    })