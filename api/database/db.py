import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
pool = None

async def create_pool():
    global pool
    pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        database=os.getenv("POSTGRES_DB"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        min_size=1,
        max_size=10,
    )


async def close_pool():
    global pool
    if pool:
        await pool.close()
