from uuid6 import uuid7

async def upsert_user(conn, github_user: dict) -> dict:
    user_id = str(uuid7())

    row = await conn.fetchrow("""
        INSERT INTO users (id, github_id, username, email, avatar_url, role)
        VALUES ($1, $2, $3, $4, $5, 'analyst')
        ON CONFLICT (github_id) DO UPDATE
            SET username = EXCLUDED.username,
                email = EXCLUDED.email,
                avatar_url = EXCLUDED.avatar_url,
                last_login_at = NOW()
        RETURNING id, github_id, username, email, avatar_url, role, is_active
    """,
        user_id,
        str(github_user["id"]),
        github_user.get("login"),
        github_user.get("email"),
        github_user.get("avatar_url"),
    )

    return dict(row)