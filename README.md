# Name Classification API

A REST API that classifies a given name by gender using the Genderize API. Built with FastAPI as part of the HNG Backend Stage 0 task.

---

## What it does

The endpoint accepts a name as a query parameter, calls the Genderize API, processes the response, and returns a structured result with gender prediction, confidence score, and a timestamp.

---

## Base URL

```
https://api-integration-data-processing-assessment-hnd-0-production.up.railway.app
```

---

## Endpoint

### GET /api/classify

Classifies a name by gender.

**Query Parameter**

| Parameter | Type   | Required | Description          |
|-----------|--------|----------|----------------------|
| name      | string | Yes      | The name to classify |

**Success Response — 200 OK**

```json
{
  "status": "success",
  "data": {
    "name": "john",
    "gender": "male",
    "probability": 0.99,
    "sample_size": 1234,
    "is_confident": true,
    "processed_at": "2026-04-01T12:00:00Z"
  }
}
```

**Error Responses**

| Status | Reason               |
|--------|----------------------|
| 400    | Bad Request          |
| 422    | Unprocessable Entity |
| 500    | Internal Server Error|
| 502    | Bad Gateway          |

All errors follow this structure:

```json
{
  "status": "error",
  "message": "<description of the error>"
}
```

---

## Processing Rules

- `count` from the Genderize response is renamed to `sample_size`
- `is_confident` is `true` only when `probability >= 0.7` AND `sample_size >= 100`. Both conditions must pass
- `processed_at` is generated dynamically on every request in UTC ISO 8601 format
- If Genderize returns a null gender or a count of zero, the API returns an error message instead of prediction data

---

## Running Locally

**Requirements**

- Python 3.9 or higher

**Install dependencies**

```bash
pip install fastapi uvicorn httpx
```

**Start the server**

```bash
uvicorn main:app --reload
```

The server runs at `http://localhost:8000`.

**Test the endpoint**

```bash
# Valid request
curl "http://localhost:8000/api/classify?name=john"

# Missing name — returns 400
curl "http://localhost:8000/api/classify"

# Empty name — returns 400
curl "http://localhost:8000/api/classify?name="

# Numeric value — returns 422
curl "http://localhost:8000/api/classify?name=123"

# Unknown name — returns error message
curl "http://localhost:8000/api/classify?name=xzqwerty"
```

---

## Deployment

Deployed on Railway. The server is configured to run with:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**requirements.txt**

```
fastapi
uvicorn
httpx
```

---

## Tech Stack

- FastAPI
- httpx
- Genderize API