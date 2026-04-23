from dotenv import load_dotenv
import os
load_dotenv()

if os.getenv("MODULE_ENV") == 'development':
    from database import db
else:
    from api.database import db

async def delete_profile(id: str):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM profiles WHERE id = $1",
            id
        )

        return {
            "message": "No Content"
        }