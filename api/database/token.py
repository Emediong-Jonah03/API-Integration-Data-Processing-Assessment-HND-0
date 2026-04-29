import hashlib
from datetime import datetime, timedelta

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def store_refresh_token(conn, user_id: str, raw_token: str):
    await conn.execute("""
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES ($1, $2, $3)
    """,
        user_id,
        hash_token(raw_token),
        datetime.utcnow() + timedelta(minutes=5)
    )

async def rotate_refresh_token(conn, old_raw: str, new_raw: str) -> str:
    old_hash = hash_token(old_raw)

    row = await conn.fetchrow("""
        SELECT id, user_id FROM refresh_tokens
        WHERE token_hash = $1
          AND revoked = FALSE
          AND expires_at > NOW()
    """, old_hash)

    if not row:
        raise ValueError("Invalid or expired refresh token")

    async with conn.transaction():
        await conn.execute("""
            UPDATE refresh_tokens SET revoked = TRUE WHERE id = $1
        """, row["id"])
        await store_refresh_token(conn, str(row["user_id"]), new_raw)

    return str(row["user_id"])