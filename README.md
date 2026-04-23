# Insighta Labs — Intelligence Query Engine

A queryable demographic intelligence API built with FastAPI and PostgreSQL. Supports advanced filtering, sorting, pagination, and natural language querying over 2026 demographic profiles.

---

## Base URL

```
https://emedev-hng0.vercel.app
```

---

## Endpoints

### GET /api/profiles

Returns profiles with optional filtering, sorting, and pagination.

**Query Parameters**

| Parameter              | Type   | Description                              |
|------------------------|--------|------------------------------------------|
| gender                 | string | `male` or `female`                       |
| age_group              | string | `child`, `teenager`, `adult`, `senior`   |
| country_id             | string | ISO 2-letter code e.g. `NG`, `KE`        |
| min_age                | int    | Minimum age (inclusive)                  |
| max_age                | int    | Maximum age (inclusive)                  |
| min_gender_probability | float  | Minimum gender confidence score          |
| min_country_probability| float  | Minimum country confidence score         |
| sort_by                | string | `age`, `created_at`, `gender_probability`|
| order                  | string | `asc` (default) or `desc`               |
| page                   | int    | Page number, default `1`                 |
| limit                  | int    | Results per page, default `10`, max `50` |

**Example**

```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc
```

**Response**

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 142,
  "data": [ ... ]
}
```

---

### GET /api/profiles/search

Accepts a plain English query and converts it into filters.

**Query Parameters**

| Parameter | Type   | Description             |
|-----------|--------|-------------------------|
| q         | string | Natural language query  |
| page      | int    | Page number, default 1  |
| limit     | int    | Max 50, default 10      |

**Example**

```
GET /api/profiles/search?q=young males from nigeria&page=1&limit=10
```

---

### GET /api/profiles/{id}

Returns a single profile by UUID.

### POST /api/profiles

Creates a new profile by fetching data from Genderize, Agify, and Nationalize APIs.

**Body**
```json
{ "name": "Emeka" }
```

### DELETE /api/profiles/{id}

Deletes a profile by UUID.

---

## Natural Language Parsing

The `/api/profiles/search` endpoint uses rule-based keyword parsing — no AI or LLMs involved. The query string is lowercased and matched against a fixed set of keywords.

### Gender Keywords

| Query contains | Maps to         |
|----------------|-----------------|
| `female`       | `gender=female` |
| `male`         | `gender=male`   |

`female` is checked before `male` to avoid "male" matching inside "female".

### Age Group Keywords

| Query contains | Maps to                          |
|----------------|----------------------------------|
| `child`        | `age_group=child`                |
| `teenager`     | `age_group=teenager`             |
| `adult`        | `age_group=adult`                |
| `senior`       | `age_group=senior`               |
| `young`        | `min_age=16`, `max_age=24`       |

> `young` is a parser-only concept. It is not a stored age group.

### Age Range Keywords

| Query pattern        | Maps to          |
|----------------------|------------------|
| `above N` / `over N` | `min_age=N`      |
| `below N` / `under N`| `max_age=N`      |

These override `young` if both appear in the same query.

### Country Keywords

Countries are matched by full name (case-insensitive). Multi-word names like "united states of america" are matched before shorter names to prevent partial collisions.

**Supported examples:**

| Query contains        | Maps to             |
|-----------------------|---------------------|
| `nigeria`             | `country_id=NG`     |
| `kenya`               | `country_id=KE`     |
| `ghana`               | `country_id=GH`     |
| `tanzania`            | `country_id=TZ`     |
| `angola`              | `country_id=AO`     |
| `ethiopia`            | `country_id=ET`     |
| `uganda`              | `country_id=UG`     |
| `cameroon`            | `country_id=CM`     |
| `senegal`             | `country_id=SN`     |
| `benin`               | `country_id=BJ`     |
| `united kingdom`      | `country_id=UK`     |
| `united states`       | `country_id=US`     |
| `australia`           | `country_id=AU`     |

### Example Mappings

| Query                          | Filters applied                                  |
|-------------------------------|--------------------------------------------------|
| `young males from nigeria`    | gender=male, min_age=16, max_age=24, country=NG  |
| `females above 30`            | gender=female, min_age=30                        |
| `adult males from kenya`      | gender=male, age_group=adult, country=KE         |
| `teenagers below 18`          | age_group=teenager, max_age=18                   |
| `people from angola`          | country_id=AO                                    |

If no recognizable keywords are found, the API returns:

```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## Limitations

- **No synonym support** — "men" and "women" do not map to gender. Only "male" and "female" work.
- **No compound age logic** — "between 20 and 40" is not supported. Use `min_age` and `max_age` query params directly on `/api/profiles` instead.
- **Countries not in the map return no country filter** — unrecognised country names are silently ignored rather than returning an error.
- **Single country per query** — "people from nigeria or kenya" only matches the first country found.
- **"young" and age_group conflict** — if a query contains both "young" and "adult", age_group takes priority and the young range is ignored.
- **No spelling correction** — "nigria" or "femal" will not match anything.
- **No negation** — "not female" or "excluding seniors" is not supported.

---

## Error Responses

All errors follow this structure:

```json
{ "status": "error", "message": "<description>" }
```

| Status | Reason                    |
|--------|---------------------------|
| 400    | Missing or empty parameter|
| 422    | Invalid parameter type    |
| 404    | Profile not found         |
| 502    | External API failure      |

---

## Running Locally

```bash
git clone <repo-url>
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
DATABASE_URL=postgresql://user:password@host/dbname
MODULE_ENV=development
```

Seed the database:

```bash
PYTHONPATH=. python database/seed.py
```

Start the server:

```bash
uvicorn index:app --reload
```

---

## Tech Stack

- FastAPI
- asyncpg
- PostgreSQL (Neon)
- uuid7
- Genderize / Agify / Nationalize APIs