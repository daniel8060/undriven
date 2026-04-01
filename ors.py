import concurrent.futures
import requests
import config

BASE_URL = "https://api.openrouteservice.org"


class ORSError(Exception):
    pass


def _headers():
    return {"Authorization": config.ORS_API_KEY}


def geocode(place: str) -> tuple[float, float]:
    params = {"api_key": config.ORS_API_KEY, "text": place, "size": 1}

    focus = getattr(config, "GEOCODE_FOCUS", None)
    if focus:
        params["focus.point.lon"] = focus["lon"]
        params["focus.point.lat"] = focus["lat"]

    resp = requests.get(
        f"{BASE_URL}/geocode/search",
        headers=_headers(),
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        raise ORSError(f"No geocoding results for: {place!r}")
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    return (coords[0], coords[1])


def reverse_geocode(lon: float, lat: float) -> str:
    """Return a human-readable address label for a coordinate pair."""
    resp = requests.get(
        f"{BASE_URL}/geocode/reverse",
        headers=_headers(),
        params={"api_key": config.ORS_API_KEY, "point.lon": lon, "point.lat": lat, "size": 1},
        timeout=5,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        raise ORSError(f"No reverse geocoding results for ({lon}, {lat})")
    return features[0]["properties"].get("label", "")


def autocomplete(text: str, focus: dict | None = None) -> list[dict]:
    """Return up to 5 place suggestions for partial input.

    focus — optional {"lon": float, "lat": float} that overrides GEOCODE_FOCUS in config.
    """
    params = {"api_key": config.ORS_API_KEY, "text": text, "size": 5}

    resolved_focus = focus or getattr(config, "GEOCODE_FOCUS", None)
    if resolved_focus:
        params["focus.point.lon"] = resolved_focus["lon"]
        params["focus.point.lat"] = resolved_focus["lat"]

    resp = requests.get(
        f"{BASE_URL}/geocode/autocomplete",
        headers=_headers(),
        params=params,
        timeout=5,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    return [
        {
            "label": f["properties"].get("label", ""),
            "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1],
        }
        for f in features
    ]


def driving_miles(start: str, end: str) -> float:
    # Geocode both endpoints in parallel to halve round-trip time
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_start = pool.submit(geocode, start)
        fut_end   = pool.submit(geocode, end)
        start_coord = fut_start.result()
        end_coord   = fut_end.result()

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
