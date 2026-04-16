from api_url import get_data

async def nationalize_profile(name: str):
    data = await get_data(name)
    nationality_data = data.get("nationality_data", {})
    country_list = nationality_data.get("country", [])
    
    if not country_list:
        return {"country_id": None, "country_probability": 0}
    
    top_country_obj = max(country_list, key=lambda x: x["probability"])
    
    return {
        "country_id": top_country_obj["country_id"],
        "country_probability": top_country_obj["probability"]
    }