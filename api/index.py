from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

if os.getenv("MODULE_ENV") == 'development':
    from api_url import get_data
    from routes.profile import profileRouter
    from middleware.validate_name import validate_name
    from database.db import create_pool, close_pool

else:
    from api.routes.profile import profileRouter
    from api.middleware.validate_name import validate_name
    from api.database.db import create_pool, close_pool
    from api.api_url import get_data

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from mangum import Mangum

class Profile(BaseModel):
    gender: str
    probability: float
    sample_size: int
    is_confident: bool
    processed_at: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    print("DB connected")

    yield
    app.state.pool = await close_pool()
    print("DB closed")

app = FastAPI(lifespan=lifespan)
handler = Mangum(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

    
app.include_router(profileRouter, prefix="/api/profiles")

@app.get("/api/classify")
async def classify_name(name: str = Query(default=None)):

    if validate_name(name):
        return validate_name(name)

    data = await get_data(name)

    if isinstance(data, JSONResponse):
        return data

    if data['gender_data'].get("gender") is None or data['gender_data'].get("count", 0) == 0:
        return JSONResponse(status_code=200, content={
            "status": "error",
            "message": "No prediction available for the provided name"
        })

    probability = data['gender_data']["probability"]
    sample_size = data['gender_data']["count"]
    is_confident = probability >= 0.7 and sample_size >= 100

    return JSONResponse(status_code=200, content={
        "status": "success",
        "data": {
            "name": data['gender_data']["name"],
            "gender": data['gender_data']["gender"],
            "probability": probability,
            "sample_size": sample_size,
            "is_confident": is_confident,
            "processed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
    })



    
   

