from fastapi import HTTPException

def validate_name(name: any):
    if not name or not str(name).strip():
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Missing or empty name"}
        )

    cleaned = str(name).strip()

    if cleaned.isnumeric():
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid type"}
        )