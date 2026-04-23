import re
from dotenv import load_dotenv
import os
load_dotenv()

if os.getenv('MODULE_ENV') == 'development':
    from services.get_profile import get_all_profiles
else:
    from api.services.get_profile import get_all_profiles

COUNTRY_MAP = {
    'algeria': 'DZ',
    'angola': 'AO',
    'australia': 'AU',
    'benin': 'BJ',
    'botswana': 'BW',
    'brazil': 'BR',
    'burkina faso': 'BF',
    'burundi': 'BI',
    'cameroon': 'CM',
    'canada': 'CA',
    'cape verde': 'CV',
    'central african republic': 'CF',
    'chad': 'TD',
    'china': 'CN',
    'comoros': 'KM',
    "côte d'ivoire": 'CI',
    'djibouti': 'DJ',
    'dr congo': 'CD',
    'egypt': 'EG',
    'equatorial guinea': 'GQ',
    'eritrea': 'ER',
    'eswatini': 'SZ',
    'ethiopia': 'ET',
    'france': 'FR',
    'gabon': 'GA',
    'gambia': 'GM',
    'germany': 'DE',
    'ghana': 'GH',
    'guinea': 'GN',
    'guinea-bissau': 'GW',
    'india': 'IN',
    'japan': 'JP',
    'kenya': 'KE',
    'lesotho': 'LS',
    'liberia': 'LR',
    'libya': 'LY',
    'madagascar': 'MG',
    'malawi': 'MW',
    'mali': 'ML',
    'mauritania': 'MR',
    'mauritius': 'MU',
    'morocco': 'MA',
    'mozambique': 'MZ',
    'namibia': 'NA',
    'niger': 'NE',
    'nigeria': 'NG',
    'republic of the congo': 'CG',
    'rwanda': 'RW',
    'são tomé and príncipe': 'ST',
    'senegal': 'SN',
    'seychelles': 'SC',
    'sierra leone': 'SL',
    'somalia': 'SO',
    'south africa': 'ZA',
    'south sudan': 'SS',
    'sudan': 'SD',
    'tanzania': 'TZ',
    'togo': 'TG',
    'tunisia': 'TN',
    'uganda': 'UG',
    'united kingdom': 'GB',
    'united states': 'US',
    'western sahara': 'EH',
    'zambia': 'ZM',
    'zimbabwe': 'ZW'
}


def parse_nl_query(q: str):
    q = q.lower().strip()
    filters = {}

    if "female" in q:
        filters["gender"] = "female"
    elif "male" in q:
        filters["gender"] = "male"

    if "child" in q:
        filters["age_group"] = "child"
    elif "teenager" in q:
        filters["age_group"] = "teenager"
    elif "adult" in q:
        filters["age_group"] = "adult"
    elif "senior" in q:
        filters["age_group"] = "senior"
    elif "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24

    above = re.search(r"(?:above|over) (\d+)", q)
    below = re.search(r"(?:below|under) (\d+)", q)

    if above:
        filters["min_age"] = int(above.group(1))
    if below:
        filters["max_age"] = int(below.group(1))

    for word, code in sorted(COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if word in q:
            filters["country_id"] = code
            break

    if not filters:
        return None

    return filters


async def search_profiles_nl(q: str, page: int = 1, limit: int = 10):
    filters = parse_nl_query(q)
    if filters is None:
        return {"status": "error", "message": "Unable to interpret query"}

    result, err = await get_all_profiles(**filters, page=page, limit=limit)
    if err:
        return err
    return result