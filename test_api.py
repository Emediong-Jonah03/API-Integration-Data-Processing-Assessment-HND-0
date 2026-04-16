import httpx
import asyncio
import re

BASE = "http://localhost:8000"

PASS = "✓"
FAIL = "✗"

score = 0
total = 0


def check(name, passed, detail="", pts=0):
    global score, total
    total += pts

    if passed:
        score += pts
        print(f"  {PASS} {name} (+{pts}) — {detail}")
    else:
        print(f"  {FAIL} {name} (+0/{pts}) — {detail}")


async def run():
    global score, total

    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:

        print("\n── POST /api/profiles ─────────────────────")

        r = await c.post("/api/profiles?name=ella")
        check("201 or 200 response",
              r.status_code in [200, 201],
              f"HTTP {r.status_code}", pts=3)

        d = r.json().get("data", {})

        check("Has gender fields",
              isinstance(d.get("gender"), str),
              str(d.get("gender")), pts=3)

        check("Has age_group valid",
              d.get("age_group") in ["child", "teenager", "adult", "senior"],
              f"{d.get('age_group')}", pts=3)

        check("created_at ends with Z",
              str(d.get("created_at", "")).endswith("Z"),
              str(d.get("created_at")), pts=2)

        created_id = d.get("id")

        print("\n── Idempotency ─────────────────────────")

        r2 = await c.post("/api/profiles?name=ella")
        d2 = r2.json().get("data", {})

        check("Same name returns same id",
              d2.get("id") == created_id,
              f"{d2.get('id')}", pts=5)

        print("\n── GET LIST ───────────────────────────")

        r = await c.get("/api/profiles")
        body = r.json()
        items = body.get("data", [])

        check("count field exists",
              isinstance(body.get("count"), int),
              body.get("count"), pts=3)

        check("created profile exists in list",
              any(p.get("id") == created_id for p in items),
              len(items), pts=4)

        print("\n── GET BY ID ──────────────────────────")

        r = await c.get(f"/api/profiles/{created_id}")

        check("GET by id works",
              r.status_code == 200,
              f"{r.status_code}", pts=5)

        print("\n── ERROR CASES ────────────────────────")

        r = await c.post("/api/profiles?name=")
        check("empty name rejected",
              r.status_code == 400,
              r.text, pts=3)

        r = await c.post("/api/profiles?name=123")
        check("numeric name rejected",
              r.status_code == 422,
              r.text, pts=3)

    print("\n" + "=" * 40)
    print(f"SCORE: {score}/{total}")
    print("=" * 40)


asyncio.run(run())