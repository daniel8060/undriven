import requests

from backend import config

GEOCODING_URL  = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL     = "https://places.googleapis.com/v1/places:autocomplete"
ROUTES_URL     = "https://routes.googleapis.com/directions/v2:computeRoutes"


class MapsError(Exception):
    pass


def _key():
    return config.GOOGLE_MAPS_API_KEY


def geocode(place: str) -> tuple[float, float]:
    """Resolve an address string to (lon, lat). Used by diagnostic endpoints."""
    params = {"address": place, "key": _key(), "region": "us"}

    focus = getattr(config, "GEOCODE_FOCUS", None)
    if focus:
        params["bounds"] = f"{focus['lat']},{focus['lon']}|{focus['lat']},{focus['lon']}"

    resp = requests.get(GEOCODING_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK" or not data.get("results"):
        raise MapsError(f"No geocoding results for: {place!r} (status: {data['status']})")
    loc = data["results"][0]["geometry"]["location"]
    return (loc["lng"], loc["lat"])


def reverse_geocode(lon: float, lat: float) -> str:
    resp = requests.get(
        GEOCODING_URL,
        params={"latlng": f"{lat},{lon}", "key": _key()},
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK" or not data.get("results"):
        raise MapsError(f"No reverse geocoding results for ({lon}, {lat})")
    return data["results"][0]["formatted_address"]


def autocomplete(text: str, focus: dict | None = None) -> list[dict]:
    """Return up to 5 address suggestions using the Places API (New).

    focus — optional {"lon": float, "lat": float} to bias results.
    Falls back to GEOCODE_FOCUS from config if not provided.
    """
    resolved = focus or getattr(config, "GEOCODE_FOCUS", None)
    body = {
        "input": text,
        "includedRegionCodes": ["us", "ca"],
    }
    if resolved:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": resolved["lat"], "longitude": resolved["lon"]},
                "radius": 50000.0,
            }
        }

    resp = requests.post(
        PLACES_URL,
        headers={"X-Goog-Api-Key": _key(), "Content-Type": "application/json"},
        json=body,
        timeout=5,
    )
    if not resp.ok:
        raise MapsError(f"Places API HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    return [
        {"label": s["placePrediction"]["text"]["text"], "lon": None, "lat": None}
        for s in data.get("suggestions", [])
        if "placePrediction" in s
    ]


def driving_miles(start: str, end: str) -> float:
    """Return driving distance in miles using the Routes API."""
    resp = requests.post(
        ROUTES_URL,
        headers={
            "X-Goog-Api-Key": _key(),
            "X-Goog-FieldMask": "routes.distanceMeters",
            "Content-Type": "application/json",
        },
        json={
            "origin":      {"address": start},
            "destination": {"address": end},
            "travelMode":  "DRIVE",
        },
        timeout=15,
    )
    if not resp.ok:
        raise MapsError(f"Routes API HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    if "error" in data:
        msg = data["error"].get("message", str(data["error"]))
        raise MapsError(f"Routes API error: {msg}")
    try:
        return data["routes"][0]["distanceMeters"] / 1609.344
    except (KeyError, IndexError) as exc:
        raise MapsError(f"Unexpected Routes API response: {exc}") from exc
