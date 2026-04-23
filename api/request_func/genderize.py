import os
from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel
from typing import Optional

if os.getenv("MODULE_ENV") == 'development':
    from api_url import get_data
else :
    from api.api_url import get_data
class Genderize(BaseModel):
    gender: Optional[str]
    probability: Optional[float] = 0
    count: Optional[int] = 0


async def gender_profile(name: str): 
    data = await get_data(name)
    raw_gender = data.get('gender_data')
    
    if not raw_gender or raw_gender.get("gender") is None:
        return {
            "gender": None,
            "gender_probability": 0,
            "sample_size": 0
        }

    gender_profile = Genderize(**raw_gender)

    return {
        "gender": gender_profile.gender,
        "gender_probability": gender_profile.probability,
        "sample_size": gender_profile.count,
    }