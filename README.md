# Insighta Labs — Intelligence Query Engine (Backend)

A queryable demographic intelligence API built with **FastAPI** and **PostgreSQL**. Supports advanced filtering, sorting, pagination, natural language querying, and GitHub OAuth 2.0 + PKCE authentication over 2,026 demographic profiles.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Authentication Flow](#authentication-flow)
3. [CLI Usage](#cli-usage)
4. [Token Handling](#token-handling)
5. [Role Enforcement](#role-enforcement)
6. [Natural Language Parsing](#natural-language-parsing)
7. [API Endpoints](#api-endpoints)
8. [Error Responses](#error-responses)
9. [Running Locally](#running-locally)
10. [Tech Stack](#tech-stack)

---

## System Architecture

The project is split across **three separate repositories** that each own a distinct layer of the stack:

```
┌─────────────────────────────────────────────────────┐
│                   Three Repositories                │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  insighta-   │  │  insighta-   │  │ insighta-│  │
│  │  backend     │  │  frontend    │  │   cli    │  │
│  │  (this repo) │  │  (React/Vite)│  │ (Python) │  │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  │
│         │                 │               │         │
└─────────┼─────────────────┼───────────────┼─────────┘
          │                 │               │
          ▼                 ▼               ▼
   ┌─────────────────────────────────────────────┐
   │         PostgreSQL (Neon / local)           │
   │                                             │
   │  tables: profiles, users, refresh_tokens   │
   └─────────────────────────────────────────────┘
```

### Repository Roles

| Repo | Responsibility |
|------|---------------|
| **insighta-backend** (this repo) | FastAPI app — auth, profile CRUD, NL search, token rotation |
| **insighta-frontend** | React/Vite SPA — browser OAuth flow, profile dashboard |
| **insighta-cli** | Python CLI — headless OAuth via PKCE + all API commands |

### Backend Internal Layout

```
api/
├── index.py              # FastAPI app factory, middleware, lifespan
├── api_url.py            # Concurrent Genderize / Agify / Nationalize fetchers
├── auth/
│   ├── router.py         # /auth/github, /auth/github/callback, /auth/refresh, /auth/logout
│   ├── dependencies.py   # get_current_user(), require_role() FastAPI dependencies
│   └── jwt.py            # create_access_token(), decode_access_token(), generate_refresh_token()
├── database/
│   ├── db.py             # asyncpg connection pool (create_pool / close_pool)
│   ├── users.py          # upsert_user() — insert or update on GitHub ID conflict
│   ├── token.py          # store_refresh_token(), rotate_refresh_token(), hash_token()
│   ├── schema.sql        # DDL: profiles, users, refresh_tokens tables
│   └── seed.py / seed.sql # 2,026 profile seed data loader
├── routes/
│   └── profile.py        # /api/profiles — list, create, get, delete, search, export
├── services/
│   ├── create_profile_service.py  # Calls Genderize/Agify/Nationalize, writes to DB
│   ├── get_profile.py             # Filtered/paginated SELECT queries
│   ├── search_profiles_nl.py      # NL query → filters → get_all_profiles()
│   └── delete_profile.py         # DELETE by UUID
└── middleware/
    └── validate_name.py  # Reject blank or non-alpha name inputs
```

### Database Schema

```sql
-- Demographic data (seeded from external APIs)
CREATE TABLE profiles (
    id                  UUID PRIMARY KEY,
    name                VARCHAR NOT NULL UNIQUE,
    gender              VARCHAR NOT NULL CHECK (gender IN ('male', 'female')),
    gender_probability  FLOAT NOT NULL,
    age                 INTEGER NOT NULL,
    age_group           VARCHAR NOT NULL,
    country_id          VARCHAR(2) NOT NULL,
    country_name        VARCHAR NOT NULL,
    country_probability FLOAT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OAuth users (created on first login)
CREATE TABLE users (
    id            TEXT PRIMARY KEY,    -- UUID v7 string
    github_id     VARCHAR UNIQUE NOT NULL,
    username      VARCHAR,
    email         VARCHAR,
    avatar_url    VARCHAR,
    role          VARCHAR DEFAULT 'analyst',
    is_active     BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Refresh token store (hashed, rotated on every use)
CREATE TABLE refresh_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked    BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Authentication Flow

All authentication uses **GitHub OAuth 2.0** with **PKCE** (Proof Key for Code Exchange) to prevent authorization code interception. There is no username/password login.

### PKCE Step-by-Step

```
CLI / Browser                Backend                      GitHub
     │                          │                            │
     │  1. Generate locally:     │                            │
     │     code_verifier (random │                            │
     │     64-byte URL-safe str) │                            │
     │     code_challenge =      │                            │
     │       SHA-256(verifier)   │                            │
     │       |> base64url        │                            │
     │                          │                            │
     │  2. GET /auth/github      │                            │
     │     ?code_challenge=...   │                            │
     │ ─────────────────────────►│                            │
     │                          │  Stores challenge in       │
     │                          │  pkce_store[state]         │
     │                          │                            │
     │  3. 302 redirect ────────►│──── redirect ─────────────►│
     │                          │    ?client_id              │
     │                          │    &redirect_uri           │
     │                          │    &state                  │
     │                          │                            │
     │  4. User approves on GitHub                           │
     │ ◄────────────────────────────── callback w/ code ─────│
     │                          │                            │
     │  5. GET /auth/github/callback                         │
     │     ?code=...&state=...   │                            │
     │     &code_verifier=...    │                            │
     │ ─────────────────────────►│                            │
     │                          │  Re-computes challenge     │
     │                          │  SHA-256(verifier)|b64url  │
     │                          │  Must equal stored value   │
     │                          │                            │
     │                          │  6. POST to GitHub         │
     │                          │──── exchange code ────────►│
     │                          │◄─── gh_access_token ───────│
     │                          │                            │
     │                          │  7. GET /user from GitHub  │
     │                          │──── bearer gh_token ──────►│
     │                          │◄─── github_user JSON ──────│
     │                          │                            │
     │                          │  8. upsert_user() in DB    │
     │                          │  9. Issue access + refresh │
     │◄──── access_token ───────│                            │
     │      refresh_token       │                            │
```

### Cookie vs Bearer Token

The backend supports two delivery modes for the same tokens:

| Mode | Endpoint | Token delivery | Best for |
|------|----------|---------------|---------|
| **Bearer** | `GET /auth/github/callback` | JSON response body — `access_token` + `refresh_token` | CLI, mobile, API clients |
| **HttpOnly Cookie** | `GET /auth/github/callback/web` | `Set-Cookie` headers (`httponly`, `samesite=lax`) | Browser SPA (prevents JS access to tokens) |

The cookie endpoint sets:

```
Set-Cookie: access_token=<jwt>;  HttpOnly; SameSite=Lax; Max-Age=180
Set-Cookie: refresh_token=<raw>; HttpOnly; SameSite=Lax; Max-Age=300
```

After setting cookies it performs a `302` redirect to `http://localhost:5173/dashboard`.

All protected API routes expect the **Bearer** mode: `Authorization: Bearer <access_token>`.

---

## CLI Usage

The CLI is a separate Python tool (`insighta-cli`) that handles the full PKCE flow headlessly — it generates the code verifier, opens a browser, captures the callback, and stores tokens locally.

> All commands below assume the CLI binary is installed as `insighta`.
> The backend base URL defaults to `https://emedev-hng0.vercel.app`.

### Authentication

```bash
# Open a browser to start the GitHub OAuth flow.
# Locally handles PKCE and stores tokens after callback.
insighta login

# Show the currently logged-in GitHub username and role.
insighta whoami

# Revoke your refresh token and clear local credentials.
insighta logout
```

### Profile Listing & Filtering

```bash
# List profiles (defaults: page=1, limit=10)
insighta profiles list

# Filter by gender and country
insighta profiles list --gender male --country NG

# Filter by age range, sorted descending by age
insighta profiles list --min-age 25 --max-age 40 --sort-by age --order desc

# Paginate results
insighta profiles list --page 2 --limit 25

# All filter flags
insighta profiles list \
  --gender female \
  --country KE \
  --age-group adult \
  --min-age 18 \
  --max-age 35 \
  --min-gender-probability 0.85 \
  --min-country-probability 0.70 \
  --sort-by gender_probability \
  --order desc \
  --page 1 \
  --limit 50
```

### Natural Language Search

```bash
# Plain English query — no flags needed
insighta profiles search "young males from nigeria"
insighta profiles search "females above 30"
insighta profiles search "adult males from kenya"
insighta profiles search "teenagers below 18"
insighta profiles search "people from angola"

# With pagination
insighta profiles search "senior females from ghana" --page 1 --limit 20
```

### Single Profile Lookup

```bash
# Get a profile by its UUID
insighta profiles get 018f1a2b-3c4d-7e5f-a6b7-c8d9e0f12345
```

### Create a Profile (admin only)

```bash
# Fetches gender/age/nationality from external APIs and stores result
insighta profiles create --name "Emeka"
insighta profiles create --name "Amara"
```

### Delete a Profile (admin only)

```bash
insighta profiles delete 018f1a2b-3c4d-7e5f-a6b7-c8d9e0f12345
```

### Export Profiles to CSV

```bash
# Export all profiles matching filters as a CSV download
insighta profiles export --gender female --country NG
insighta profiles export --age-group senior --output ./seniors.csv
```

### Token Refresh

```bash
# Manually force a token refresh (normally done automatically)
insighta token refresh
```

---

## Token Handling

### Access Token

| Property | Value |
|----------|-------|
| Format | Signed JWT (`HS256`) |
| Payload | `sub` (user UUID v7), `role`, `username`, `exp` |
| Lifetime | **3 minutes** (`timedelta(minutes=3)`) |
| Secret | `JWT_SECRET_KEY` env variable |
| Transport | `Authorization: Bearer <token>` header |

```python
# auth/jwt.py
def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=3)
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

### Refresh Token

| Property | Value |
|----------|-------|
| Format | Random 64-byte URL-safe string (`secrets.token_urlsafe(64)`) |
| Stored as | SHA-256 hash in `refresh_tokens` table (raw token never persisted) |
| Lifetime | **5 minutes** (`expires_at = NOW() + interval '5 minutes'`) |
| Transport | JSON body field `refresh_token` on `POST /auth/refresh` |

### Token Rotation

Every call to `POST /auth/refresh` performs an **atomic rotation**:

1. Hash the incoming `refresh_token` with SHA-256.
2. Look up the hash in `refresh_tokens` — reject if `revoked = TRUE` or `expires_at < NOW()`.
3. Inside a **database transaction**:
   - Mark the old row `revoked = TRUE`.
   - Insert a new row with a freshly generated token hash and a new 5-minute expiry.
4. Issue a new short-lived access token and return both tokens.

This means **each refresh token can only be used once**. A reused or leaked token will be rejected immediately.

```python
# database/token.py — atomic rotation
async with conn.transaction():
    await conn.execute(
        "UPDATE refresh_tokens SET revoked = TRUE WHERE id = $1", row["id"]
    )
    await store_refresh_token(conn, str(row["user_id"]), new_raw)
```

### Logout

`POST /auth/logout` accepts `{ "refresh_token": "..." }`, hashes it, and sets `revoked = TRUE` — invalidating the session without needing to touch the access token (which will expire naturally within 3 minutes).

---

## Role Enforcement

### Roles

| Role | Assigned | Permissions |
|------|----------|------------|
| `analyst` | Default on first login via GitHub | Read-only: list, search, export, get by ID |
| `admin` | Manually promoted in DB | Full access: all analyst permissions + create + delete |

### `require_role()` Dependency

The `require_role()` function in `auth/dependencies.py` is a **FastAPI dependency factory**. It returns an async dependency that:

1. Extracts and validates the Bearer token via `get_current_user()`.
2. Checks that the resolved user's `role` field is in the allowed roles list.
3. Raises `HTTP 403 Access denied` if the role doesn't match.

```python
# auth/dependencies.py
def require_role(*roles: str):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(
                403,
                detail={"status": "error", "message": "Access denied"}
            )
        return current_user
    return role_checker
```

### Applied in Routes

```python
# routes/profile.py

# POST /api/profiles — admin only
@profileRouter.post("/", status_code=201)
async def api_profiles(
    body: ProfileRequest,
    current_user: dict = Depends(require_role("admin")),   # 403 for analysts
):
    ...

# GET /api/profiles — any authenticated user
@profileRouter.get("/")
async def api_profiles_get(
    ...
    current_user: dict = Depends(get_current_user),        # 401 if no token
):
    ...

# DELETE /api/profiles/{id} — admin only
@profileRouter.delete("/{id}", status_code=204)
async def api_profiles_delete(
    id: str,
    current_user: dict = Depends(require_role("admin")),   # 403 for analysts
):
    ...
```

### `get_current_user()` Chain

```
Bearer header present?
        │ no  → HTTP 401
        │ yes
        ▼
decode_access_token(token)
        │ invalid/expired → HTTP 401
        │ valid
        ▼
SELECT user from DB by payload["sub"]
        │ not found → HTTP 401
        │ found
        ▼
user["is_active"] == True?
        │ no  → HTTP 403
        │ yes → return user dict
```

### Promoting an Analyst to Admin

No admin endpoint is exposed. Promote via a direct DB query:

```sql
UPDATE users SET role = 'admin' WHERE username = 'your-github-username';
```

---

## Natural Language Parsing

`api/services/search_profiles_nl.py` converts a free-text English query into structured filter parameters — **no AI, LLMs, or embeddings involved**. It is entirely rule-based.

### How It Works

```
User query: "young males from nigeria"
               │
               ▼
          q.lower().strip()
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
 Gender    Age group      Country
 check     check          lookup
    │          │              │
"male" ──► gender=male    "nigeria" ──► country_id=NG
           "young" ──► min_age=16, max_age=24
               │
               ▼
    filters = {gender: male, min_age: 16, max_age: 24, country_id: NG}
               │
               ▼
    get_all_profiles(**filters, page=page, limit=limit)
               │
               ▼
         Paginated DB result
```

### Parsing Rules (in order)

**1. Gender** — checked in priority order to prevent `"female"` matching the `"male"` substring:

```python
if "female" in q:       # checked first
    filters["gender"] = "female"
elif "male" in q:
    filters["gender"] = "male"
```

**2. Age Group & Young Range**:

```python
if "child" in q:
    filters["age_group"] = "child"
elif "teenager" in q:
    filters["age_group"] = "teenager"
elif "adult" in q:
    filters["age_group"] = "adult"
elif "senior" in q:
    filters["age_group"] = "senior"
elif "young" in q:
    filters["min_age"] = 16    # not a stored age_group
    filters["max_age"] = 24
```

**3. Numeric Age Ranges** (override `young` if present):

```python
above = re.search(r"(?:above|over) (\d+)", q)
below = re.search(r"(?:below|under) (\d+)", q)

if above:
    filters["min_age"] = int(above.group(1))
if below:
    filters["max_age"] = int(below.group(1))
```

**4. Country Lookup** — multi-word names are matched **longest-first** to prevent `"niger"` matching inside `"nigeria"`:

```python
for word, code in sorted(COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
    if word in q:
        filters["country_id"] = code
        break
```

The `COUNTRY_MAP` covers 55+ countries (all 54 African Union members + UK, US, Australia, Canada, Brazil, China, India, Japan, France, Germany).

### Example Mappings

| Query | Filters produced |
|-------|-----------------|
| `young males from nigeria` | `gender=male, min_age=16, max_age=24, country_id=NG` |
| `females above 30` | `gender=female, min_age=30` |
| `adult males from kenya` | `gender=male, age_group=adult, country_id=KE` |
| `teenagers below 18` | `age_group=teenager, max_age=18` |
| `people from angola` | `country_id=AO` |
| `senior females from ghana` | `gender=female, age_group=senior, country_id=GH` |

### Known Limitations

- **No synonym support** — `"men"` / `"women"` / `"boys"` / `"girls"` do not resolve. Only `"male"` and `"female"` work.
- **No compound age ranges** — `"between 20 and 40"` is unsupported. Use `min_age` / `max_age` on `GET /api/profiles` directly.
- **Single country per query** — only the first match wins.
- **`"young"` vs `age_group` conflict** — if both appear, the named `age_group` keyword takes priority and `young` is ignored.
- **No spelling correction** — `"nigerria"` or `"femal"` match nothing.
- **No negation** — `"not female"` or `"excluding seniors"` are not supported.
- **Unrecognised countries** — silently ignored; no error is returned.

If no recognisable keyword is found at all:

```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## API Endpoints

All endpoints under `/api/profiles` require:
- A valid `Authorization: Bearer <access_token>` header.
- An `X-API-Version: 1` header.

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/auth/github` | None | Initiate PKCE OAuth flow |
| `GET` | `/auth/github/callback` | None | Exchange code → Bearer tokens |
| `GET` | `/auth/github/callback/web` | None | Exchange code → HttpOnly cookies |
| `POST` | `/auth/refresh` | None (refresh token) | Rotate refresh token, get new access token |
| `POST` | `/auth/logout` | None (refresh token) | Revoke refresh token |

### Profiles

| Method | Path | Role | Description |
|--------|------|------|-------------|
| `GET` | `/api/profiles` | Any authenticated | List profiles with filters & pagination |
| `GET` | `/api/profiles/search?q=...` | Any authenticated | Natural language search |
| `GET` | `/api/profiles/export` | Any authenticated | Download filtered profiles as CSV |
| `GET` | `/api/profiles/{id}` | Any authenticated | Get single profile by UUID |
| `POST` | `/api/profiles` | **admin** only | Create profile (calls external APIs) |
| `DELETE` | `/api/profiles/{id}` | **admin** only | Delete profile by UUID |

### Query Parameters for `GET /api/profiles`

| Parameter | Type | Description |
|-----------|------|-------------|
| `gender` | string | `male` or `female` |
| `age_group` | string | `child`, `teenager`, `adult`, `senior` |
| `country_id` | string | ISO 2-letter code e.g. `NG`, `KE` |
| `min_age` | int | Minimum age (inclusive) |
| `max_age` | int | Maximum age (inclusive) |
| `min_gender_probability` | float | Minimum confidence score |
| `min_country_probability` | float | Minimum confidence score |
| `sort_by` | string | `age`, `created_at`, `gender_probability` |
| `order` | string | `asc` (default) or `desc` |
| `page` | int | Page number, default `1` |
| `limit` | int | Results per page, default `10`, max `50` |

---

## Error Responses

All errors follow this envelope:

```json
{ "status": "error", "message": "<description>" }
```

| Status | Reason |
|--------|--------|
| `400` | Missing or invalid parameter |
| `401` | Missing, invalid, or expired token |
| `403` | Correct token but insufficient role, or inactive account |
| `404` | Profile not found |
| `422` | Pydantic validation error |
| `429` | Rate limit exceeded (10 req/min on auth endpoints) |
| `502` | External API (Genderize / Agify / Nationalize) failure |

---

## Running Locally

```bash
git clone <backend-repo-url>
cd task0

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file at the project root:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/insighta_db
MODULE_ENV=development
GITHUB_CLIENT_ID=<your-github-oauth-app-client-id>
GITHUB_CLIENT_SECRET=<your-github-oauth-app-client-secret>
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
JWT_SECRET_KEY=<at-least-32-random-hex-chars>
```

Apply the schema and seed profiles:

```bash
psql $DATABASE_URL -f api/database/schema.sql
PYTHONPATH=. python api/database/seed.py
```

Start the development server:

```bash
uvicorn api.index:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.

### Promote your GitHub account to admin

```bash
psql $DATABASE_URL \
  -c "UPDATE users SET role = 'admin' WHERE username = 'your-github-username';"
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.135 |
| Database driver | asyncpg 0.31 |
| Database | PostgreSQL (Neon in production / local Docker in dev) |
| Token signing | python-jose (HS256 JWT) |
| OAuth | GitHub OAuth 2.0 + PKCE |
| HTTP client | httpx (async) |
| Rate limiting | slowapi |
| CSRF protection | starlette-csrf |
| Deployment | Vercel (via Mangum ASGI adapter) |
| CI | GitHub Actions (flake8 lint on PRs) |
| External APIs | Genderize.io · Agify.io · Nationalize.io |
| ID generation | uuid7 (UUID v7 — time-sortable) |