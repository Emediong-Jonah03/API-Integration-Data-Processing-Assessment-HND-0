import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
pool = None

async def create_pool():
    global pool
    pool = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL"),
        min_size=1,
        max_size=10,
        ssl="require"
    )


async def close_pool():
    global pool
    if pool:
        await pool.close()
