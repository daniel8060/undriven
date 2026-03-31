import requests
import config

BASE_URL = "https://api.openrouteservice.org"


class ORSError(Exception):
    pass


def _headers():
    return {"Authorization": config.ORS_API_KEY}


def geocode(place: str) -> tuple[float, float]:
    resp = requests.get(
        f"{BASE_URL}/geocode/search",
        headers=_headers(),
        params={"api_key": config.ORS_API_KEY, "text": place, "size": 1},
        timeout=10,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        raise ORSError(f"No geocoding results for: {place!r}")
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    return (coords[0], coords[1])


def driving_miles(start: str, end: str) -> float:
    start_coord = geocode(start)
    end_coord = geocode(end)

    resp = requests.post(
        f"{BASE_URL}/v2/directions/driving-car",
        headers={**_headers(), "Content-Type": "application/json"},
        params={"api_key": config.ORS_API_KEY},
        json={"coordinates": [list(start_coord), list(end_coord)]},
        timeout=15,
    )
    if resp.status_code != 200:
        raise ORSError(f"ORS directions failed ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    try:
        metres = data["routes"][0]["summary"]["distance"]
    except (KeyError, IndexError) as exc:
        raise ORSError(f"Unexpected ORS response structure: {exc}") from exc

    return metres / 1609.344
