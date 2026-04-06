from unittest.mock import MagicMock, patch
import pytest
import gmaps


def _geocode_response(lon, lat, formatted="Test Address"):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "status": "OK",
        "results": [{
            "geometry": {"location": {"lat": lat, "lng": lon}},
            "formatted_address": formatted,
        }],
    }
    return mock


def _distance_response(metres):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "status": "OK",
        "rows": [{"elements": [{"status": "OK", "distance": {"value": metres}}]}],
    }
    return mock


def _autocomplete_response(predictions):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"status": "OK", "predictions": predictions}
    return mock


# ── geocode ──────────────────────────────────────────────────────────────────

def test_geocode_returns_lon_lat():
    with patch("gmaps.requests.get", return_value=_geocode_response(-122.04, 37.37)):
        lon, lat = gmaps.geocode("1324 Chesapeake Terrace, Sunnyvale CA")
    assert lon == pytest.approx(-122.04)
    assert lat == pytest.approx(37.37)


def test_geocode_raises_on_zero_results():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    with patch("gmaps.requests.get", return_value=mock):
        with pytest.raises(gmaps.MapsError, match="No geocoding results"):
            gmaps.geocode("nowhere special")


def test_geocode_passes_focus_bounds():
    with patch("gmaps.requests.get", return_value=_geocode_response(-122.04, 37.37)) as mock_get:
        with patch.object(gmaps.config, "GEOCODE_FOCUS", {"lon": -122.04, "lat": 37.37}):
            gmaps.geocode("Main St")
    params = mock_get.call_args[1]["params"]
    assert "bounds" in params
    assert "37.37" in params["bounds"]


# ── autocomplete ─────────────────────────────────────────────────────────────

def test_autocomplete_returns_label_list():
    predictions = [
        {"description": "1324 Chesapeake Terrace, Sunnyvale, CA, USA"},
        {"description": "225 Red Oak Drive West, Sunnyvale, CA, USA"},
    ]
    with patch("gmaps.requests.get", return_value=_autocomplete_response(predictions)):
        results = gmaps.autocomplete("Chesapeake")
    assert len(results) == 2
    assert results[0]["label"] == "1324 Chesapeake Terrace, Sunnyvale, CA, USA"
    # Google autocomplete doesn't return coordinates
    assert results[0]["lon"] is None
    assert results[0]["lat"] is None


def test_autocomplete_passes_location_bias():
    with patch("gmaps.requests.get", return_value=_autocomplete_response([])) as mock_get:
        gmaps.autocomplete("park", focus={"lon": -122.04, "lat": 37.37})
    params = mock_get.call_args[1]["params"]
    assert "location" in params
    assert "37.37" in params["location"]
    assert params["radius"] == 50000


def test_autocomplete_falls_back_to_config_focus():
    with patch("gmaps.requests.get", return_value=_autocomplete_response([])) as mock_get:
        with patch.object(gmaps.config, "GEOCODE_FOCUS", {"lon": -122.04, "lat": 37.37}):
            gmaps.autocomplete("Main St")
    params = mock_get.call_args[1]["params"]
    assert "37.37" in params["location"]


def test_autocomplete_restricts_to_north_america():
    with patch("gmaps.requests.get", return_value=_autocomplete_response([])) as mock_get:
        gmaps.autocomplete("park")
    params = mock_get.call_args[1]["params"]
    assert "country:us" in params["components"]
    assert "country:ca" in params["components"]


# ── driving_miles ─────────────────────────────────────────────────────────────

def test_driving_miles_converts_metres():
    # 16093.44 metres = 10.0 miles
    with patch("gmaps.requests.get", return_value=_distance_response(16093.44)):
        miles = gmaps.driving_miles("Sunnyvale CA", "San Jose CA")
    assert miles == pytest.approx(10.0, rel=1e-4)


def test_driving_miles_raises_on_api_error():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"status": "REQUEST_DENIED", "rows": []}
    with patch("gmaps.requests.get", return_value=mock):
        with pytest.raises(gmaps.MapsError, match="Distance Matrix API error"):
            gmaps.driving_miles("A", "B")


def test_driving_miles_raises_on_no_route():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "status": "OK",
        "rows": [{"elements": [{"status": "NOT_FOUND"}]}],
    }
    with patch("gmaps.requests.get", return_value=mock):
        with pytest.raises(gmaps.MapsError, match="No route found"):
            gmaps.driving_miles("A", "B")
