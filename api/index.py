from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from mangum import Mangum
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

if os.getenv("MODULE_ENV") == 'development':
    from routes.profile import profileRouter
    from middleware.validate_name import validate_name
    from database.db import create_pool, close_pool
    from auth.router import auth_router
else:
    from api.routes.profile import profileRouter
    from api.middleware.validate_name import validate_name
    from api.database.db import create_pool, close_pool
    from api.auth.router import auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    print("DB connected")
    yield
    app.state.pool = await close_pool()
    print("DB closed")

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
handler = Mangum(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration}ms")
    return response

app.include_router(profileRouter, prefix="/api/profiles")
app.include_router(auth_router)