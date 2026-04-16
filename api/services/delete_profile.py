from database import db

async def delete_profile(id: str):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM profiles WHERE id = $1",
            id
        )

        return {
            "message": "No Content"
        }