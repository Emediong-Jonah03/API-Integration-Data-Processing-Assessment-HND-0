from fastapi import HTTPException
import re

def validate_name(name: any):
    if not name or not str(name).strip():
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Missing or empty parameter"}
        )

    cleaned = str(name).strip()

    if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid parameter type"}
        )

    return cleaned