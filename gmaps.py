import requests
import config

BASE_URL = "https://maps.googleapis.com/maps/api"


class MapsError(Exception):
    pass


def _key():
    return config.GOOGLE_MAPS_API_KEY


def geocode(place: str) -> tuple[float, float]:
    """Resolve an address string to (lon, lat). Used by diagnostic endpoints."""
    params = {"address": place, "key": _key(), "region": "us"}

    focus = getattr(config, "GEOCODE_FOCUS", None)
    if focus:
        # Degenerate bounding box biases results toward the focus area without hard-filtering.
        params["bounds"] = f"{focus['lat']},{focus['lon']}|{focus['lat']},{focus['lon']}"

    resp = requests.get(f"{BASE_URL}/geocode/json", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK" or not data.get("results"):
        raise MapsError(f"No geocoding results for: {place!r} (status: {data['status']})")
    loc = data["results"][0]["geometry"]["location"]
    return (loc["lng"], loc["lat"])


def reverse_geocode(lon: float, lat: float) -> str:
    resp = requests.get(
        f"{BASE_URL}/geocode/json",
        params={"latlng": f"{lat},{lon}", "key": _key()},
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK" or not data.get("results"):
        raise MapsError(f"No reverse geocoding results for ({lon}, {lat})")
    return data["results"][0]["formatted_address"]


def autocomplete(text: str, focus: dict | None = None) -> list[dict]:
    """Return up to 5 address suggestions for partial input.

    focus — optional {"lon": float, "lat": float} to bias results toward a location.
    Falls back to GEOCODE_FOCUS from config if not provided.
    """
    resolved = focus or getattr(config, "GEOCODE_FOCUS", None)
    params = {
        "input": text,
        "key": _key(),
        "types": "geocode",
        "components": "country:us|country:ca",
    }
    if resolved:
        params["location"] = f"{resolved['lat']},{resolved['lon']}"
        params["radius"] = 50000  # 50 km bias radius

    resp = requests.get(f"{BASE_URL}/place/autocomplete/json", params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    # Google Place Autocomplete doesn't return coordinates — lon/lat are None.
    # The server geocodes addresses at submission time via Distance Matrix.
    return [
        {"label": p["description"], "lon": None, "lat": None}
        for p in data.get("predictions", [])
    ]


def driving_miles(start: str, end: str) -> float:
    """Return driving distance in miles between two address strings.

    Google Distance Matrix geocodes the addresses internally — no separate geocoding step needed.
    """
    resp = requests.get(
        f"{BASE_URL}/distancematrix/json",
        params={
            "origins": start,
            "destinations": end,
            "mode": "driving",
            "key": _key(),
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "OK":
        raise MapsError(f"Distance Matrix API error: {data['status']}")
    try:
        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            raise MapsError(f"No route found between {start!r} and {end!r}: {element['status']}")
        return element["distance"]["value"] / 1609.344
    except (KeyError, IndexError) as exc:
        raise MapsError(f"Unexpected Distance Matrix response structure: {exc}") from exc
