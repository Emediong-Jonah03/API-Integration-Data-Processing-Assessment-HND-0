from pydantic import BaseModel, ValidationError
from api.api_url import get_data
from typing import Optional

class Agify(BaseModel):
    age: Optional[int]
    
async def agify_profile(name: str):
    data = await get_data(name)
    raw_age_data = data.get('age_data')
    
    try:
        profile = Agify(**raw_age_data) 
    except (TypeError, ValueError, ValidationError):
        return {"age": None, "age_group": None}  

    if profile.age is None:
        return {"age": None, "age_group": None} 

    if profile.age <= 12:
        group = "child"
    elif profile.age <= 19:
        group = "teenager"
    elif profile.age <= 59:
        group = "adult"
    else:
        group = "senior"
    
    return {
        "age": profile.age,
        "age_group": group
    }