import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from uuid6 import uuid7
import db

async def seed():
    await db.create_pool()
    with open("database/seed_profiles.json") as f:
        profiles = json.load(f)["profiles"]

    async with db.pool.acquire() as conn:
        for p in profiles:
            await conn.execute("""
                INSERT INTO profiles (id, name, gender, gender_probability, age, age_group, country_id, country_name, country_probability)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8, $9)
                ON CONFLICT (name) DO NOTHING
            """, uuid7(), p["name"], p["gender"], p["gender_probability"], p["age"],
                p["age_group"], p["country_id"], p["country_name"], p["country_probability"])

    print("Seeded.")
    await db.pool.close()

asyncio.run(seed())